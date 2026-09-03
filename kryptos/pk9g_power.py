"""Stage 2. Among constructions CONSISTENT with PK9's IoC, which would have been DETECTED by the
residue-class test that came out null on PK9?  For each hypothesis: simulate M ciphertexts at
n=144, and for each run the IDENTICAL test used on PK9 (mean per-class IoC for p=2..12, z-scored
against that ciphertext's OWN shuffle null, familywise max over p).  Power = P(max-z >= the
shuffle-null 95th percentile).  PK9 itself scored max-z = +2.43 (familywise p = 0.124)."""
import sys, json, time, numpy as np
sys.path.insert(0,'.')
from lib import *
rng=np.random.default_rng(101); t0=time.time()
n=144; M=300; NS=200          # sims per hypothesis, shuffles per sim
PERIODS=list(range(2,13))
ENGw=None
CORP=np.concatenate([np.array([AZ.index(c) for c in PT[k]],dtype=np.int64) for k in sorted(PT)])
NC=len(CORP)
def ptwin(N):
    st=rng.integers(0,NC-n,size=N); return CORP[(st[:,None]+np.arange(n)[None,:])]

def classioc(A,p):
    """A (N,n) -> (N,) mean per-class IoC, via one flat bincount per period."""
    N=A.shape[0]; cls=np.arange(n)%p
    code=(cls[None,:]*26+A).ravel()
    off=(np.arange(N)*(26*p)).repeat(n)
    cnt=np.bincount(off+code,minlength=N*26*p).reshape(N,p,26)
    L=np.bincount(cls,minlength=p).astype(float)
    v=(cnt*(cnt-1)).sum(2)/ (L*(L-1))[None,:]
    return v.mean(1)

def maxz(A,chunk=40):
    """for each row of A, the familywise max over p of the z of classioc vs its own shuffle null"""
    N=A.shape[0]; out=np.zeros(N)
    for s in range(0,N,chunk):
        blk=A[s:s+chunk]; b=blk.shape[0]
        rows=[blk]
        for _ in range(NS): rows.append(np.stack([rng.permutation(r) for r in blk]))
        BIG=np.concatenate(rows,0)                       # ((NS+1)*b, n)
        Z=np.zeros((b,len(PERIODS)))
        for j,p in enumerate(PERIODS):
            v=classioc(BIG,p).reshape(NS+1,b)
            nul=v[1:]; Z[:,j]=(v[0]-nul.mean(0))/nul.std(0,ddof=1)
        out[s:s+b]=Z.max(1)
    return out

# shuffle-null 95th percentile of the same familywise max-z, taken from PK9's own null
C9=np.array([AZ.index(c) for c in CT['pk9']])
SH=np.stack([rng.permutation(C9) for _ in range(1200)])
NULLMAX=maxz(SH)
THR=float(np.percentile(NULLMAX,95)); OBS9=float(maxz(C9[None,:])[0])
print(f"PK9 observed familywise max-z = {OBS9:+.2f};  shuffle-null 95th pct = {THR:.2f}"
      f"  (null mean {NULLMAX.mean():.2f} sd {NULLMAX.std(ddof=1):.2f})  [{time.time()-t0:.0f}s]")

def perm_alpha(N): return np.stack([rng.permutation(26) for _ in range(N)])
H={}
P=ptwin(M)
def add(name,C): H[name]=C
add('flat/random long key (CONTROL: should be ~5%)',(P+rng.integers(0,26,size=(M,n)))%26)
add('monoalphabetic (CONTROL)',np.take_along_axis(perm_alpha(M),P,1))
for p in [3,4,5,6,7,8,9,10,12]:
    k=rng.integers(0,26,size=(M,p)); add(f'periodic p={p} (iid key)',(P+k[:,np.arange(n)%p])%26)
for p in [4,5,6,7]:
    k=np.stack([rng.permutation(26)[:p] for _ in range(M)])
    add(f'periodic p={p} (DISTINCT letters)',(P+k[:,np.arange(n)%p])%26)
# transposition-innermost variant, to show the residue test is transposition-invariant
Pt=np.stack([rng.permutation(r) for r in P])
k6=rng.integers(0,26,size=(M,6)); add('periodic p=6 UNDER a transposition',(Pt+k6[:,np.arange(n)%6])%26)
for k_ in [3,4,5,6,7]:
    sub=np.stack([rng.permutation(26)[:k_] for _ in range(M)])
    add(f'APERIODIC, {k_} distinct alphabets',(P+np.take_along_axis(sub,rng.integers(0,k_,size=(M,n)),1))%26)
for Pp in [9,12,18,24,36,144]:
    sub=np.stack([rng.permutation(26)[:4] for _ in range(M)])
    key=np.take_along_axis(sub,rng.integers(0,4,size=(M,Pp)),1)
    add(f'period {Pp} key, 4 distinct letters',(P+key[:,np.arange(n)%Pp])%26)
K=ptwin(M); add('running key, same alphabet',(P+K)%26)
add('running key thru keyed alphabet',(P+np.take_along_axis(perm_alpha(M),K,1))%26)
pr=rng.integers(0,26,size=(M,8)); add('plaintext autokey (primer 8)',(P+np.concatenate([pr,P[:,:n-8]],1))%26)
add('split: 1st half monoA, 2nd half monoB',np.concatenate(
    [np.take_along_axis(perm_alpha(M),P[:,:72],1),np.take_along_axis(perm_alpha(M),P[:,72:],1)],1))
add('split: 1st half mono, 2nd half flat',np.concatenate(
    [np.take_along_axis(perm_alpha(M),P[:,:72],1),(P[:,72:]+rng.integers(0,26,size=(M,72)))%26],1))
A=perm_alpha(M)
add('Quagmire-III keyed alpha, period 6',np.take_along_axis(A,(np.take_along_axis(np.argsort(A,1),P,1)
    +rng.integers(0,26,size=(M,6))[:,np.arange(n)%6])%26,1))
from math import gcd
Mh=200
MM=np.zeros((Mh,2,2),dtype=np.int64)
for i in range(Mh):
    while True:
        m=rng.integers(0,26,size=(2,2))
        if gcd(int(round(np.linalg.det(m)))%26,26)==1: break
    MM[i]=m
B=P[:Mh].reshape(Mh,-1,2); add('Hill 2x2 invertible',np.einsum('nij,nbj->nbi',MM,B).reshape(Mh,-1)%26)

rows=[]
print(f"\n{'construction':44s} {'M':>4} {'mean maxz':>9} {'sd':>5} {'POWER':>6} {'P(<=PK9 obs)':>12}")
for name,C in H.items():
    mz=maxz(C); pw=float((mz>=THR).mean()); pl=float((mz<=OBS9).mean())
    print(f"{name:44s} {C.shape[0]:4d} {mz.mean():+9.2f} {mz.std(ddof=1):5.2f} {pw:6.3f} {pl:12.3f}")
    rows.append(dict(name=name,M=int(C.shape[0]),maxz_mean=float(mz.mean()),maxz_sd=float(mz.std(ddof=1)),
                     power=pw,p_le_pk9obs=pl))
json.dump(dict(pk9_obs_maxz=OBS9,null_95=THR,null_mean=float(NULLMAX.mean()),
               null_sd=float(NULLMAX.std(ddof=1)),M=M,NS=NS,periods=PERIODS,rows=rows),
          open('results/pk9_power.json','w'),indent=1)
print(f"\nhypotheses={len(H)} sims={sum(c.shape[0] for c in H.values())} "
      f"shuffles/sim={NS}  wall {time.time()-t0:.0f}s")
