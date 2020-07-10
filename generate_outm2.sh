#get in the errant folder(! cd drive/My Drive/errant)
! pip3 install stanfordnlp -U
#import stanfordnlp
#stanfordnlp.download('hi')
! pip3 install python-Levenshtein
! rm errant/out.m2
! python3 errant/parallel_to_m2.py -orig "../fairseq-gec/data/hiwiki.src" -cor "../fairseq-gec/data/hiwiki.tgt" -out "errant/out.m2"
