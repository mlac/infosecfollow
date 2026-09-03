"""Byte-faithful copy of mk_cat.py's per-cell search (layout + joint_masked), so that
nulls are produced by the IDENTICAL code path that produced the real maxima."""
import sys; sys.path.insert(0,'.')
import numpy as np
from lib import KA, AZ
import mk_lib as M

ALPH={'KA':KA,'AZ':AZ}
AMIN,AMAX=3,12
K=200
CONFIGS=[('KA','KA','sub'),('KA','KA','add'),('AZ','AZ','sub'),('KA','AZ','sub')]

def layout(kind,n,a,b):
    i=np.arange(n)
    if kind in ('C','CR'):
        P=a+b; r=i%P
        posA=np.nonzero(r<a)[0]; posB=np.nonzero(r>=a)[0]
        cmA=r[posA]; cmB=r[posB]-a
        fA=np.zeros(n,dtype=np.int64); fA[posA]=cmA
        fB=np.zeros(n,dtype=np.int64); fB[posB]=cmB
    else:
        posA=np.nonzero(i%2==0)[0]; posB=np.nonzero(i%2==1)[0]
        cmA=(posA//2)%a; cmB=(posB//2)%b
        fA=np.zeros(n,dtype=np.int64); fA[posA]=cmA
        fB=np.zeros(n,dtype=np.int64); fB[posB]=cmB
    return posA,cmA,posB,cmB,fA,fB,posA,posB

def joint_masked(C,WA,WB,fA,fB,mA,mB,iA,iB,mode):
    n=len(C)
    SA=np.zeros((len(iA),n),dtype=np.int16); SA[:,mA]=WA[iA][:,fA[mA]]
    SB=np.zeros((len(iB),n),dtype=np.int16); SB[:,mB]=WB[iB][:,fB[mB]]
    base=C.astype(np.int16); best=-1.0; bi=bj=0
    for x in range(SA.shape[0]):
        if mode=='sub':   R=(base[None,:]-SA[x][None,:]-SB)%26
        elif mode=='add': R=(base[None,:]+SA[x][None,:]+SB)%26
        else:             R=(SA[x][None,:]+SB-base[None,:])%26
        v=M.ioc_rows_fast(R); j=int(v.argmax())
        if v[j]>best: best,bi,bj=float(v[j]),x,j
    return best,bi,bj

def run_text(ct,byl,WM,WMR,kinds=('C','CR','D'),configs=None,tag=''):
    """returns list of run-records: one per (config,kind) = max over the 100-cell grid,
    exactly the unit that produced the reported family maxima."""
    configs=configs or CONFIGS
    runs=[]; cells=0
    for (ta,ka,md) in configs:
        C=M.to_idx(ct,ALPH[ta]); n=len(C)
        for kind in kinds:
            best=None
            for a in range(AMIN,AMAX+1):
                for b in range(AMIN,AMAX+1):
                    posA,cmA,posB,cmB,fA,fB,mA,mB=layout(kind,n,a,b)
                    WB=WMR[ka][b] if kind=='CR' else WM[ka][b]
                    sA=M.score_parts(C,WM[ka][a],[(posA,cmA)],md)
                    sB=M.score_parts(C,WB,[(posB,cmB)],md)
                    if sA is None or sB is None: continue
                    _,_,_,zA=M.zstat(sA); _,_,_,zB=M.zstat(sB)
                    iA=np.argsort(-sA)[:K]; iB=np.argsort(-sB)[:K]
                    j,x,y=joint_masked(C,WM[ka][a],WB,fA,fB,mA,mB,iA,iB,md)
                    cells+=1
                    if best is None or j>best['joint']:
                        best={'cfg':f'{ta}/{ka}/{md}','kind':kind,'a':a,'b':b,
                              'joint':round(j,5),'zA':round(float(zA),3),'zB':round(float(zB),3),
                              'wA':byl[a][int(iA[x])],'wB':byl[b][int(iB[y])],'tag':tag}
            runs.append(best)
    return runs,cells

def relabel(ct,rng,alpha=KA):
    """structure-preserving null: random monoalphabetic re-labelling.  Preserves n, the
    exact letter-frequency profile, the ciphertext IoC, and EVERY positional coincidence
    pattern (which letters repeat where).  Destroys only the additive relation to any key."""
    perm=rng.permutation(26)
    ai={c:i for i,c in enumerate(alpha)}
    return ''.join(alpha[perm[ai[c]]] for c in ct)
