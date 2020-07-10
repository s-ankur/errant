class HindiStemmer:
    def __init__(self):
      self.Suffix_list=['A', 'AeM', 'awA', 'Ane', 'egA','i', 'AoM' ,'awI', 'UMgA' ,'egI','I' ,'iyAM' ,'IM' ,'UMgI' ,'AegA','u' ,'iyoM' ,'awIM', 'AUMgA' ,'AegI','U' ,'AiyAM' ,'awe' ,'AUMgI', 'AyA','e' ,'AiyoM', 'AwA' ,'eMge', 'Ae','o' ,'AMh' ,'AwI' ,'eMgI' ,'AI','eM', 'iyAMh' ,'AwIM', 'AeMge' ,'AIM','oM' ,'AiyAMh' ,'Awe' ,'AeMgI' ,'ie','AM' ,'awAeM' ,'manA' ,'oge' 'Ao','uAM' ,'awAoM', 'anI' ,'ogI', 'Aie','ueM' ,'anAeM' ,'ane' ,'Aoge' ,'akara','uoM' ,'anAoM', 'AnA', 'AogI'
      , 'Akara']
    def stem(self,word):
      for i in range(len(word)):
        if word[i:] in self.Suffix_list:
          return word[:i]
