"""DERIVED null: run the identical concat/interleave and single-word searches on REAL
sibling Kryptos-family ciphertexts (PK3/PK6/PK7, truncated to n=153/144/504), whose keys are
known and are NOT of these manufacture types.  A letter-shuffle destroys the positional letter
clustering that every real periodic cipher has; these surrogates keep it, so they measure the
ceiling that the shuffle null under-estimates."""
import sys, time, json, collections; sys.path.insert(0,'.')
import numpy as np
from lib import KA, AZ, CT
import mk_lib as M
ALPH={'KA':KA,'AZ':AZ}
CONFIGS=[('KA','KA','sub'),('KA','KA','add'),('AZ','AZ','sub'),('KA','AZ','sub')]
byl=M.load_words(3,12)
WM={ka:{L:M.wordmat(byl[L],ALPH[ka]) for L in byl} for ka in ('KA','AZ')}
WMR={ka:{L:WM[ka][L][:,::-1].copy() for L in byl} for ka in ('KA','AZ')}
SUR={}
for n in (153,144):
    for src in ('pk3','pk6','pk7'): SUR[(src,n)]=CT[src][:n]
for src in ('pk6','pk2'): SUR[(src,504)]=(CT['pk6']+CT['pk2']+CT['pk3'])[:504]
def layout(kind,n,a,b):
    i=np.arange(n)
    if kind in ('C','CR'):
        P=a+b; r=i%P; pA=np.nonzero(r<a)[0]; pB=np.nonzero(r>=a)[0]
        fA=np.zeros(n,dtype=np.int64); fA[pA]=r[pA]
        fB=np.zeros(n,dtype=np.int64); fB[pB]=r[pB]-a
        return pA,r[pA],pB,r[pB]-a,fA,fB
    pA=np.nonzero(i%2==0)[0]; pB=np.nonzero(i%2==1)[0]
    fA=np.zeros(n,dtype=np.int64); fA[pA]=(pA//2)%a
    fB=np.zeros(n,dtype=np.int64); fB[pB]=(pB//2)%b
    return pA,(pA//2)%a,pB,(pB//2)%b,fA,fB
def jm(C,WA,WB,fA,fB,mA,mB,iA,iB,mode):
    n=len(C)
    SA=np.zeros((len(iA),n),dtype=np.int16); SA[:,mA]=WA[iA][:,fA[mA]]
    SB=np.zeros((len(iB),n),dtype=np.int16); SB[:,mB]=WB[iB][:,fB[mB]]
    base=C.astype(np.int16); best=-1.
    for x in range(SA.shape[0]):
        R=((base[None,:]-SA[x][None,:]-SB)%26) if mode=='sub' else (
           (base[None,:]+SA[x][None,:]+SB)%26 if mode=='add' else (SA[x][None,:]+SB-base[None,:])%26)
        v=M.ioc_rows_fast(R); best=max(best,float(v.max()))
    return best
res=collections.defaultdict(list); t0=time.time()
for (src,n),ct in sorted(SUR.items()):
    for (ta,ka,md) in CONFIGS:
        C=M.to_idx(ct,ALPH[ta])
        for kind in ('C','CR','D'):
            best=-1
            for a in range(3,13):
                for b in range(3,13):
                    pA,cA,pB,cB,fA,fB=layout(kind,n,a,b)
                    WB=WMR[ka][b] if kind=='CR' else WM[ka][b]
                    sA=M.score_parts(C,WM[ka][a],[(pA,cA)],md); sB=M.score_parts(C,WB,[(pB,cB)],md)
                    iA=np.argsort(-sA)[:200]; iB=np.argsort(-sB)[:200]
                    best=max(best,jm(C,WM[ka][a],WB,fA,fB,pA,pB,iA,iB,md))
            res[f'n{n}|{kind}'].append(round(best,5))
            print(f'{src} n={n} {ta}/{ka}/{md} {kind}: {best:.5f} ({time.time()-t0:.0f}s)',flush=True)
out={k:{'runs':len(v),'mean':round(float(np.mean(v)),5),'max':max(v),'values':v} for k,v in res.items()}
json.dump(out,open('results/mk_cat_derived_null.json','w'),indent=1)
print(json.dumps(out,indent=1))
