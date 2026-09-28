"""POWER of the concat/interleave search at n=144 as a function of the plaintext's own IoC.
Builds a genuine in-family interleave instance (KA/KA/add, a=10,b=7) on real sibling
plaintext windows of differing IoC and asks whether the IDENTICAL search recovers it."""
import sys,json,time; sys.path.insert(0,'.')
import numpy as np
from lib import KA,PT,ioc
import mk_lib as M, qk_core as Q
byl=M.load_words(Q.AMIN,Q.AMAX)
WM={ka:{L:M.wordmat(byl[L],Q.ALPH[ka]) for L in byl} for ka in ('KA','AZ')}
WMR={ka:{L:WM[ka][L][:,::-1].copy() for L in byl} for ka in ('KA','AZ')}
wins=[]
for t,p in PT.items():
    for s in range(0,len(p)-144+1,12):
        wins.append((ioc(p[s:s+144]),t,s))
wins.sort()
pick=[wins[0],wins[len(wins)//2],wins[-1]]
W1,W2='ALCHEMISTS','ANNEALS'
n=144; i=np.arange(n)
posA=np.nonzero(i%2==0)[0]; posB=np.nonzero(i%2==1)[0]
ki={c:j for j,c in enumerate(KA)}
S=np.zeros(n,dtype=np.int64)
S[posA]=[ki[W1[(p//2)%10]] for p in posA]
S[posB]=[ki[W2[(p//2)%7]] for p in posB]
out=[]
for (iv,t,s) in pick:
    P=PT[t][s:s+144]
    C=(M.to_idx(P,KA)-S)%26
    ct=''.join(KA[x] for x in C)
    t0=time.time()
    runs,cells=Q.run_text(ct,byl,WM,WMR)
    b=max(runs,key=lambda r:r['joint'])
    rec=(b['wA']==W1 and b['wB']==W2 and b['kind']=='D' and b['a']==10 and b['b']==7)
    r={'src':f'{t}[{s}:{s+144}]','pt_ioc':round(iv,5),'search_max':b['joint'],
       'argmax':{k:b[k] for k in ('cfg','kind','a','b','wA','wB')},'RECOVERED':bool(rec),
       'true_signal_ioc':round(iv,5),'sec':round(time.time()-t0,1)}
    out.append(r); print(json.dumps(r),flush=True)
    json.dump(out,open('results/qk_power.json','w'),indent=1)
