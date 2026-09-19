"""Control for the RELABEL null: (1) the identical search must RECOVER a genuine in-family
interleave key at n=144; (2) after a monoalphabetic relabel of that same ciphertext the
recovery must be destroyed and the score must fall back to null level.  If both hold, the
relabel null is a legitimate signal-free draw that keeps the real positional structure."""
import sys,json,time; sys.path.insert(0,'.')
import numpy as np
from lib import KA,AZ,PT,ioc
import mk_lib as M, qk_core as Q

byl=M.load_words(Q.AMIN,Q.AMAX)
WM={ka:{L:M.wordmat(byl[L],Q.ALPH[ka]) for L in byl} for ka in ('KA','AZ')}
WMR={ka:{L:WM[ka][L][:,::-1].copy() for L in byl} for ka in ('KA','AZ')}
# synthetic: interleave key a=10 (ALCHEMISTS) b=7 (CRUCIBL->use ANNEALS), cfg KA/KA/add, n=144
P=PT['pk5'][:144]
W1,W2='ALCHEMISTS','ANNEALS'
n=144; i=np.arange(n)
posA=np.nonzero(i%2==0)[0]; posB=np.nonzero(i%2==1)[0]
ki={c:j for j,c in enumerate(KA)}
S=np.zeros(n,dtype=np.int64)
S[posA]=[ki[W1[(p//2)%10]] for p in posA]
S[posB]=[ki[W2[(p//2)%7]] for p in posB]
Pi=M.to_idx(P,KA)
# mode 'add' means decrypt R=C+S, so encrypt C=P-S
C=(Pi-S)%26
ct=''.join(KA[x] for x in C)
print('synthetic ct_ioc',round(ioc(ct),5),'pt_ioc',round(ioc(P),5),flush=True)
res={}
t0=time.time()
runs,cells=Q.run_text(ct,byl,WM,WMR,tag='true')
res['true']={'max':max(r['joint'] for r in runs),'best':max(runs,key=lambda r:r['joint']),'cells':cells}
print('TRUE max',res['true']['max'],res['true']['best'],f'{time.time()-t0:.0f}s',flush=True)
rng=np.random.default_rng(4242)
res['relabel']=[]; res['shuffle']=[]
for d in range(2):
    ct2=Q.relabel(ct,rng)
    runs,_=Q.run_text(ct2,byl,WM,WMR,tag=f'relab{d}')
    b=max(runs,key=lambda r:r['joint'])
    res['relabel'].append({'max':b['joint'],'best':b})
    print('RELABEL',d,b['joint'],b['wA'],b['wB'],b['kind'],f'{time.time()-t0:.0f}s',flush=True)
for d in range(1):
    ct2=M.shuffled(ct,rng)
    runs,_=Q.run_text(ct2,byl,WM,WMR,tag=f'shuf{d}')
    b=max(runs,key=lambda r:r['joint'])
    res['shuffle'].append({'max':b['joint'],'best':b})
    print('SHUFFLE',d,b['joint'],b['wA'],b['wB'],b['kind'],f'{time.time()-t0:.0f}s',flush=True)
json.dump(res,open('results/qk_relabel_control.json','w'),indent=1)
