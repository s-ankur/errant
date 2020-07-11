from pathlib import Path

import Levenshtein

from .hindi_stemmer import HindiStemmer


# Load word list


def load_word_list(path) -> set:
    with open(path) as word_list:
        return {word.strip() for word in word_list}


# Load Universal Dependency POS Tags map file.
# https://universaldependencies.org/tagset-conversion/en-penn-uposf.html
# https://universaldependencies.org/tagset-conversion/hi-conll-uposf.html


def load_pos_map(path):
    map_dict = {}
    with open(path) as map_file:
        for line in map_file:
            line = line.split("\n")
            # Change ADP to PREP for readability
            if line[1] == "ADP":
                map_dict[line[0]] = "PREP"
            # Change PROPN to NOUN; we don't need a prop noun tag
            elif line[1] == "PROPN":
                map_dict[line[0]] = "NOUN"
            # Change CCONJ to CONJ
            elif line[1] == "CCONJ":
                map_dict[line[0]] = "CONJ"
            # Otherwise
            else:
                map_dict[line[0]] = line[1].strip()
        # Add some spacy PTB tags not in the original mapping.
        map_dict['""'] = "PUNCT"
        map_dict["SP"] = "SPACE"
        map_dict["ADD"] = "X"
        map_dict["GW"] = "X"
        map_dict["NFP"] = "X"
        map_dict["XX"] = "X"
    return map_dict


# Classifier resources
base_dir = Path(__file__).resolve().parent
# Lancaster Stemmer
stemmer = HindiStemmer()
# GB English word list (inc -ise and -ize)
spell = load_word_list(base_dir / "resources" / "big.txt")
# Part of speech map file
pos_map = load_pos_map(base_dir / "resources" / "hi-ptb-map")
# Open class coarse POS tags (strings)
open_pos2 = {"ADJ", "ADV", "NOUN", "VERB", "ADP", "PRON"}
# Rare POS tags that make uninformative error categories
rare_pos = {"INTJ", "NUM", "SYM", "X"}
# Special auxiliaries in contractions.
aux_conts = {}
# Some dep labels that map to pos tags.
dep_map = {
    "acomp": "ADJ",
    "amod": "ADJ",
    "advmod": "ADV",
    "det": "DET",
    "prep": "PREP",
    "prt": "PART",
    "punct": "PUNCT"}


# Input: An Edit object
# Output: The same Edit object with an updated error type


class Classifier:
    @staticmethod
    def classify(edit) -> None:
        # Nothing to nothing is a detected but not corrected edit
        if not edit.o_toks and not edit.c_toks:
            edit.type = "UNK"
        # Missing
        elif not edit.o_toks and edit.c_toks:
            op = "M:"
            cat = get_one_sided_type(edit.c_toks)
            edit.type = op + cat
        # Unnecessary
        elif edit.o_toks and not edit.c_toks:
            op = "U:"
            cat = get_one_sided_type(edit.o_toks)
            edit.type = op + cat
        # Replacement
        else:
            # Same to same is a detected but not corrected edit
            if edit.o_str == edit.c_str:
                edit.type = "UNK"
            # Replacement case
            else:
                op = "R:"
                cat = get_two_sided_type(edit.o_toks, edit.c_toks)
                edit.type = op + cat
        o_join = " ".join(o_tok.text for o_tok in edit.o_toks)
        c_join = " ".join(c_tok.text for c_tok in edit.c_toks)
        print(o_join, c_join, edit.type)


# Input: Spacy tokens
# Output: A list of pos and dep tag strings


def get_edit_info(toks: list) -> (list, list):
    pos = []
    dep = []
    for tok in toks:
        if tok.upos in pos_map:
            pos.append(pos_map[tok.upos])
        else:
            pos.append(tok.xpos)
        dep.append(tok.dependency_relation)
    return pos, dep


# Input: Spacy tokens
# Output: An error type string based on input tokens from orig or cor
# When one side of the edit is null, we can only use the other side


def get_one_sided_type(toks: list) -> str:
    # Extract pos tags and parse info from the toks
    pos_list, dep_list = get_edit_info(toks)
    # Auxiliary verbs
    if set(dep_list).issubset({"aux", "aux:pass"}):
        return "VERB:TENSE"
    # POS-based tags. Ignores rare, uninformative categories
    if len(set(pos_list)) == 1 and pos_list[0] not in rare_pos:
        return pos_list[0]
    # More POS-based tags using special dependency labels
    if len(set(dep_list)) == 1 and dep_list[0] in dep_map.keys():
        return dep_map[dep_list[0]]
    # To-infinitives and phrasal verbs
    if set(pos_list) == {"PART", "VERB"}:
        return "VERB"
    # Tricky cases
    else:
        return "OTHER"


# Input 1: Original tokens
# Input 2: Corrected tokens
# Output: An error type string based on orig AND cor

def get_two_sided_type(o_toks: list, c_toks: list) -> str:
    # Extract pos tags and parse info from the toks as lists
    o_pos, o_dep = get_edit_info(o_toks)
    c_pos, c_dep = get_edit_info(c_toks)

    # Orthography; i.e. whitespace and/or case errors.
    if is_only_orth_change(o_toks, c_toks):
        return "ORTH"
    # Word Order; only matches exact reordering.
    if is_exact_reordering(o_toks, c_toks):
        return "WO"

    # 1:1 replacements (very common)
    if len(o_toks) == len(c_toks) == 1:
        o_tok = o_toks[0]
        c_tok = c_toks[0]

        o_feat = dict(map(lambda x: x.split('='), o_tok.feats.split('|')))
        c_feat = dict(map(lambda x: x.split('='), o_tok.feats.split('|')))

        # 1. SPELLING AND INFLECTION
        # Only check alphabetical strings on the original side
        # Spelling errors take precedence over POS errors; this rule is ordered

        if is_spelling(o_tok.text, c_tok.text):
            return 'SPELL'

        if "PROPN" in {o_tok.upos, c_tok.upos}:
            return "PROPN"

        if o_tok.text not in spell:
            char_ratio = Levenshtein.ratio(o_tok.text, c_tok.text)
            # Ratio > 0.5 means both side share at least half the same chars.
            # WARNING: THIS IS AN APPROXIMATION.
            if char_ratio > 0.5:
                return "SPELL"
            # If ratio is <= 0.5, the error is more complex e.g. tolk -> say
            else:
                return "OTHER"

        # 2. MORPHOLOGY
        # Only ADJ, ADV, NOUN and VERB can have inflectional changes.
        lemma_ratio = Levenshtein.ratio(o_tok.lemma, c_tok.lemma)
        print("lema", lemma_ratio, o_tok.upos, c_tok.upos)
        # print(o_tok,c_tok)
        if (lemma_ratio >= .65) and \
                o_tok.upos in open_pos2 and \
                c_tok.upos in open_pos2:
            # Same POS on both sides
            if o_tok.upos == c_tok.upos:
                # Adjective form; e.g. comparatives
                if o_tok.upos in ("NOUN", "ADJ", "ADP"):
                    return o_tok.upos + ":INFL"

                # Verbs - various types
                if o_tok.upos in ("VERB", "AUX"):
                    print(o_feat,c_feat)
                    if o_tok.xpos == c_tok.xpos:
                        if o_feat.get('Tense') == c_feat.get('Tense') and \
                                o_feat.get('Mood') == c_feat.get('Mood') and \
                                o_feat.get('VerbForm') == c_feat.get('VerbForm') and \
                                o_feat.get('Aspect') == c_feat.get('Aspect'):
                            return "VERB:INFL"
                        else:
                            return "VERB:FORM"

            else:
                return "MORPH"

        # Derivational morphology.
        if stemmer.stem(o_toks[0].text) == stemmer.stem(c_toks[0].text) and \
                o_pos[0] in open_pos2 and \
                c_pos[0] in open_pos2:
            return "MORPH"

        # 3. GENERAL
        # Auxiliaries with different lemmas
        if o_tok.dependency_relation.startswith("aux") and o_tok.dependency_relation.startswith("aux"):
            return "VERB:FORM"

        if o_tok.upos == o_tok.upos and o_tok.upos in (
                "VERB", "ADP", "PRON", "ADJ") and o_tok.dependency_relation == c_tok.dependency_relation:
            return o_tok.upos

        # Tricky cases.
        else:
            return "OTHER"

    # Multi-token replacements (uncommon)
    # All auxiliaries
    if set(o_dep + c_dep).issubset({"aux", "auxpass"}):
        return "VERB:TENSE"
    # All same POS
    if len(set(o_pos + c_pos)) == 1:
        # Final verbs with the same lemma are tense; e.g. eat -> has eaten
        if o_pos[0] == "VERB" and \
                o_toks[-1].lemma == c_toks[-1].lemma:
            return "VERB:TENSE"
        # POS-based tags.
        elif o_pos[0] not in rare_pos:
            return o_pos[0]
    # All same special dep labels.
    if len(set(o_dep + c_dep)) == 1 and \
            o_dep[0] in dep_map.keys():
        return dep_map[o_dep[0]]
    # Infinitives, gerunds, phrasal verbs.
    if set(o_pos + c_pos) == {"PART", "VERB"}:
        # Final verbs with the same lemma are form; e.g. to eat -> eating
        if o_toks[-1].lemma == c_toks[-1].lemma:
            return "VERB:FORM"
        # Remaining edits are often verb; e.g. to eat -> consuming, look at -> see
        else:
            return "VERB"
    # Possessive nouns; e.g. friends -> friend 's
    if (o_pos == ["NOUN", "PART"] or c_pos == ["NOUN", "PART"]) and \
            o_toks[0].lemma == c_toks[0].lemma:
        return "NOUN:POSS"
    # Adjective forms with "most" and "more"; e.g. more free -> freer
    if (o_toks[0] in {"अधिकतम", "अधिक", "परम", "ज्यादा"} or
        c_toks[0].text in {"अधिकतम", "अधिक", "परम", "ज्यादा"}) and \
            o_toks[-1].lemma == c_toks[-1].lemma and \
            len(o_toks) <= 2 and len(c_toks) <= 2:
        return "ADJ:FORM"

    # Tricky cases.
    else:
        return "OTHER"


# Input 1: Original Token
# Input 2: Corrected token
# Output: Boolean; whether edit is a pronunciational spelling variance yi -> ii etc

def is_spelling(o_tok: str, c_tok: str) -> bool:
    for orig_pair in (('ये', 'ए'), ('यी', 'ई'), ('या', 'आ'), ('यीं', 'ईं'), ('आ', 'वा')):
        for pair in (orig_pair, orig_pair[::-1]):
            if o_tok.endswith(pair[0]) and c_tok.endswith(pair[1]):
                return o_tok.rstrip(pair[0]) == c_tok.strip(pair[1])
    return False


# Input 1: List of Original tokens
# Input 2: List of Corrected tokens
# Output: Boolean; the difference between orig and cor is only whitespace or case


def is_only_orth_change(o_toks: list, c_toks: list) -> bool:
    o_join = "".join(o_tok.text for o_tok in o_toks)
    c_join = "".join(c_tok.text for c_tok in c_toks)
    if o_join == c_join:
        return True
    return False


# Input 1: Spacy orig tokens
# Input 2: Spacy cor tokens
# Output: Boolean; the tokens are exactly the same but in a different order


def is_exact_reordering(o_toks: list, c_toks: list) -> bool:
    # Sorting lets us keep duplicates.
    o_set = sorted(o.text for o in o_toks)
    c_set = sorted(c.text for c in c_toks)
    return o_set == c_set
