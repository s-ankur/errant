import argparse
import warnings
from contextlib import ExitStack

from errant.annotator import Annotator

warnings.simplefilter("ignore", UserWarning)


def main():
    # Parse command line args
    args = parse_args()
    print("Loading resources...")
    # Load Errantsrc/ATen/native/TensorAdvancedIndexing.cpp:573: UserWarning: masked_fill_ received a mask with dtype torch.uint8, this behavior is now deprecated,please use a mask with dtype torch.bool instead.

    annotator = Annotator()
    # Open output m2 file
    out_m2 = open(args.out, "w")
    error_count = {}

    print("Processing parallel files...")
    # Process an arbitrary number of files line by line simultaneously. Python 3.3+
    # See https://tinyurl.com/y4cj4gth
    with ExitStack() as stack:
        in_files = [stack.enter_context(open(i)) for i in [args.orig] + args.cor]
        # Process each line of all input files
        for line in zip(*in_files):
            # Get the original and all the corrected texts
            orig = line[0].strip()
            cors = line[1:]
            # Skip the line if orig is empty
            if not orig:
                continue
            # Parse orig with spacy
            orig = annotator.parse(orig, args.tok)
            # Write orig to the output m2 file
            temp1 = []
            for sent in orig.sentences:
                for word in sent.words:
                    temp1.append(word)
            out_m2.write(" ".join(["S"] + [token.text for token in temp1]) + "\n")
            out_m2.flush()
            # Loop through the corrected texts
            for cor_id, cor in enumerate(cors):
                cor = cor.strip()
                # If the texts are the same, write a noop edit
                if orig.text.strip() == cor:
                    out_m2.write(noop_edit(cor_id) + "\n")
                    if 'none' in error_count:
                        error_count['none'] += 1
                    else:
                        error_count['none'] = 1
                    out_m2.flush()

                # Otherwise, do extra processing
                else:
                    # Parse cor with spacy
                    cor = annotator.parse(cor, args.tok)
                    # Align the texts and extract and classify the edits
                    edits = annotator.annotate(orig, cor, args.lev, args.merge)
                    # Loop through the edits
                    for edit in edits:
                        # Write the edit to the output m2 file
                        out_m2.write(edit.to_m2(cor_id) + "\n")
                        if edit.type in error_count:
                            error_count[edit.type] += 1
                        else:
                            error_count[edit.type] = 1
                        out_m2.flush()
            # Write a newline when we have processed all corrections for each line
            out_m2.write("\n")
            out_m2.flush()
    out_m2.close()
    error_file = open('error_file', 'w')
    for key in error_count:
        error_file.write(str(key) + '\t' + str(error_count[key]))
    error_file.close()


#    pr.disable()
#    pr.print_stats(sort="time")

# Parse command line args
def parse_args():
    parser = argparse.ArgumentParser(
        description="Align parallel text files and extract and classify the edits.\n",
        formatter_class=argparse.RawTextHelpFormatter,
        usage="%(prog)s [-h] [options] -orig ORIG -cor COR [COR ...] -out OUT")
    parser.add_argument(
        "-orig",
        help="The path to the original text file.",
        required=True)
    parser.add_argument(
        "-cor",
        help="The paths to >= 1 corrected text files.",
        nargs="+",
        default=[],
        required=True)
    parser.add_argument(
        "-out",
        help="The output filepath.",
        required=True)
    parser.add_argument(
        "-tok",
        help="Word tokenise the text using spacy (default: False).",
        action="store_true")
    parser.add_argument(
        "-lev",
        help="Align using standard Levenshtein (default: False).",
        action="store_true")
    parser.add_argument(
        "-merge",
        help="Choose a merging strategy for automatic alignment.\n"
             "rules: Use a rule-based merging strategy (default)\n"
             "all-split: Merge nothing: MSSDI -> M, S, S, D, I\n"
             "all-merge: Merge adjacent non-matches: MSSDI -> M, SSDI\n"
             "all-equal: Merge adjacent same-type non-matches: MSSDI -> M, SS, D, I",
        choices=["rules", "all-split", "all-merge", "all-equal"],
        default="rules")
    args = parser.parse_args()
    return args


# Input: A coder id
# Output: A noop edit; i.e. text contains no edits


def noop_edit(id=0):
    return "A -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||" + str(id)


if __name__ == "__main__":
    main()
