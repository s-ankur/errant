import string


class IndicSentenceTokenizer:
    LANGUAGES = ('hindi', 'bengali', 'punjabi')
    NON_INDIC_CHAR = string.ascii_letters + "*&^@#:<>/+=-_}{[].~'()\""
    NON_INDIC = str.maketrans(NON_INDIC_CHAR, " " * len(NON_INDIC_CHAR))
    SENTENCE_END = '|।!?\n'
    ALLOWED_PUNCTUATION = ",;॰"

    def tokenize(self, text):
        for punct in self.SENTENCE_END + self.ALLOWED_PUNCTUATION:
            text = text.replace(punct, " " + punct + " ")
        pos = [0] * len(self.SENTENCE_END)
        while len(text) > 0:
            for i in range(len(self.SENTENCE_END)):
                pos[i] = text.find(self.SENTENCE_END[i])
            if not pos.count(-1) == len(pos):
                splitting_point = min([x for x in pos if not x == -1])
                if text[splitting_point] == '!':
                    m = splitting_point
                    m = m + 1
                    while m < len(text):
                        if text[m] == ' ':
                            m = m + 1
                        elif text[m] == '?':
                            splitting_point = m
                            break
                        else:
                            break
                if splitting_point + 1 < len(text) and text[splitting_point] in '?!':
                    splitting_point += 1
                sentence = text[:splitting_point + 1]
                text = text[splitting_point + 1:]
                ans = sentence
            else:
                ans = text
                text = ""
            ans = ans.strip()
            if len(ans)>1:
              yield ans
            
