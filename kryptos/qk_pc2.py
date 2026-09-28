"""CORRECTED positive control + relabel-null validation.
(NOTE: an earlier attempt used W2='ANNEALS', which is NOT in words.txt, so recovery was
impossible by construction; that run is void.  Here both true words are in the dictionary.)
1) full 1200-cell search on genuine in-family interleave instances at three plaintext IoC
   levels -> does the GLOBAL argmax recover the truth?
2) relabel and shuffle the recoverable instance -> the signal must die, and what is left is
   the ceiling that the null measures."""
import sys,json,time; sys.path.insert(0,'.')
import numpy as np
from lib import KA,PT,ioc
import mk_lib as M, qk_core as Q
byl=M.load_words(Q.AMIN,Q.AMAX)
WM={ka:{L:M.wordmat(byl[L],Q.ALPH[ka]) for L in byl} for ka in ('KA','AZ')}
WMR={ka:{L:WM[ka][L][:,::-1].copy() for L in byl} for ka in ('KA','AZ')}
W1,W2='ALCHEMISTS','FURNACE'
def build(P):
    n=len(P); a,b=len(W1),len(W2)
    posA,cmA,posB,cmB,fA,fB,mA,mB=Q.layout('D',n,a,b)
    ki={c:j for j,c in enumerate(KA)}
    S=np.zeros(n,dtype=np.int64); S[posA]=[ki[W1[c]] for c in cmA]; S[posB]=[ki[W2[c]] for c in cmB]
    return ''.join(KA[x] for x in (M.to_idx(P,KA)-S)%26)
out=[]; t0=time.time(); rng=np.random.default_rng(777)
CASES=[('pk5',36),('pk1',12),('pk4',12)]
hi=None
for (t,s) in CASES:
    P=PT[t][s:s+144]; ct=build(P)
    runs,_=Q.run_text(ct,byl,WM,WMR)
    b=max(runs,key=lambda r:r['joint'])
    rec=(b['wA']==W1 and b['wB']==W2 and b['kind']=='D' and b['a']==10 and b['b']==7)
    r={'kind':'TRUE','src':f'{t}[{s}]','pt_ioc':round(ioc(P),5),'search_max':b['joint'],
       'argmax':{k:b[k] for k in ('cfg','kind','a','b','wA','wB')},'RECOVERED':bool(rec)}
    out.append(r); print(json.dumps(r),f'{time.time()-t0:.0f}s',flush=True)
    json.dump(out,open('results/qk_pc2.json','w'),indent=1)
    if t=='pk4': hi=ct
for lbl,fn in (('RELABEL',lambda c:Q.relabel(c,rng)),('SHUFFLE',lambda c:M.shuffled(c,rng))):
    ct2=fn(hi)
    runs,_=Q.run_text(ct2,byl,WM,WMR)
    b=max(runs,key=lambda r:r['joint'])
    r={'kind':lbl+'_of_recoverable_instance','search_max':b['joint'],
       'argmax':{k:b[k] for k in ('cfg','kind','a','b','wA','wB')},
       'RECOVERED':bool(b['wA']==W1 and b['wB']==W2)}
    out.append(r); print(json.dumps(r),f'{time.time()-t0:.0f}s',flush=True)
    json.dump(out,open('results/qk_pc2.json','w'),indent=1)
