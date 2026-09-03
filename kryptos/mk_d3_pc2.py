"""Valid depth-3 positive control: only cells where the decoupling is NON-DEGENERATE
(>=3 groups on which the searched word actually varies) can carry signal."""
import sys, json; sys.path.insert(0,'.')
import numpy as np
from lib import KA, PT
import mk_lib as M
byl = M.load_words(3,5); WK = {L: M.wordmat(byl[L], KA) for L in byl}
src = (PT['pk6']+PT['pk2']+PT['pk3']+PT['pk5']+PT['pk7']); ki={c:i for i,c in enumerate(KA)}
OUT=[]
def rank(words, sc, w):
    i=words.index(w); return int((sc>sc[i]).sum())+1
W1,W2,W3='ARC','KILN','FORGE'
for n in (144,153,504):
    for L in (12,24,30,36,45,48,60):
        i=np.arange(n)
        w=[np.array([ki[c] for c in W]) for W in (W1,W2,W3)]
        S=(w[0][(i%L)%3]+w[1][(i%L)%4]+w[2][(i%L)%5])%26
        ct=''.join(KA[(ki[c]+int(S[t]))%26] for t,c in enumerate(src[:n]))
        C=M.to_idx(ct,KA)
        fa=M.map_mod(n,L,3); fb=M.map_mod(n,L,4); fc=M.map_mod(n,L,5)
        rs=[];zs=[];ng=[]
        for (own,o1,o2,la,tw) in ((fa,fb,fc,3,W1),(fb,fa,fc,4,W2),(fc,fa,fb,5,W3)):
            parts=M.keep_informative(M.parts_by_group(o1*26+o2, own)); ng.append(len(parts))
            if len(parts)<3: rs.append(None); zs.append(None); continue
            s=M.score_parts(C,WK[la],parts,'sub')
            rs.append(rank(byl[la],s,tw)); zs.append(round(float(M.zstat(s)[3]),2))
        rec = all(r==1 for r in rs if r is not None) and any(r is not None for r in rs)
        row={'n':n,'L':L,'informative_groups':ng,'ranks':rs,'z':zs,'RECOVERED':rec}
        OUT.append(row); print(row, flush=True)
json.dump(OUT, open('results/mk_d3_positive_control.json','w'), indent=1); print('D3PC DONE')
