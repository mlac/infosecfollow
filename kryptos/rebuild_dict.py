from wordfreq import top_n_list
ws=[w.upper() for w in top_n_list('en',500000) if w.isalpha() and w.isascii()]
seen=set(); out=[]
for w in ws:
    if w not in seen: seen.add(w); out.append(w)
extra=['PENTIMENTO','WHITESMITH','PELLEGRIN','KRYPTOS','QUAGMIRE','VIGENERE','BEAUFORT','GROMARK']
for e in extra:
    if e not in seen: seen.add(e); out.append(e)
open('words.txt','w').write('\n'.join(out))
from collections import Counter
c=Counter(len(w) for w in out)
print("total",len(out)); print("by length:",{L:c[L] for L in range(3,17)})
