"""POSITIVE CONTROL. Run the IDENTICAL residue-class battery + IoC k-estimate on the setter's
own SOLVED ciphertexts, where the construction is known ground truth.  If it recovers PK6's
period 6 and PK1's period 10 from ciphertext alone, its silence on PK9 is evidence."""
import sys, json, time, numpy as np
sys.path.insert(0,'.')
from lib import *
rng=np.random.default_rng(777); t0=time.time()
TRUTH={'pk1':'Q3 period 10 (PROVENANCE, 8 distinct letters)','pk2':'pure columnar transposition',
 'pk3':'Q3 period 40 (PENTIMENTOxORDINATE product)','pk4':'columnar THEN Q3 period 45 (OCHRE+VERDIGRIS)',
 'pk5':'columnar THEN running key = PK4 plaintext','pk6':'double columnar THEN Q3 period 6 (PORTAL, 6 distinct)',
 'pk7':'Hill 3x3 + period-2 additive','pk8':'UNKNOWN','pk9':'UNKNOWN','pk10':'UNKNOWN'}
NS=4000; PERIODS=list(range(2,13))
def classioc(A,p,n):
    N=A.shape[0]; cls=np.arange(n)%p
    code=(cls[None,:]*26+A).ravel(); off=(np.arange(N)*(26*p)).repeat(n)
    cnt=np.bincount(off+code,minlength=N*26*p).reshape(N,p,26)
    Lc=np.bincount(cls,minlength=p).astype(float)
    return ((cnt*(cnt-1)).sum(2)/(Lc*(Lc-1))[None,:]).mean(1)
out={}
print(f"{'ct':5s} {'n':>4} {'IoC':>7}  best-p  z     familywise p   | per-period z (p=2..12)")
for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7','pk8','pk9','pk10']:
    C=np.array([AZ.index(c) for c in CT[k]]); n=len(C)
    SH=np.stack([rng.permutation(C) for _ in range(NS)])
    A=np.concatenate([C[None,:],SH],0)
    Z=np.zeros((NS+1,len(PERIODS)))
    for j,p in enumerate(PERIODS):
        v=classioc(A,p,n); nul=v[1:]; Z[:,j]=(v-nul.mean())/nul.std(ddof=1)
    mx=Z.max(1); pfw=float((mx[1:]>=mx[0]).mean())
    bp=PERIODS[int(np.argmax(Z[0]))]
    ioc=float(((np.bincount(C,minlength=26)*(np.bincount(C,minlength=26)-1)).sum())/(n*(n-1)))
    print(f"{k:5s} {n:4d} {ioc:7.4f}   p={bp:<2d} {Z[0].max():+5.2f}  p_fw={pfw:.4f}  | "
          +" ".join(f"{z:+5.2f}" for z in Z[0]))
    out[k]={'n':n,'ioc':ioc,'best_p':bp,'max_z':float(Z[0].max()),'p_familywise':pfw,
            'z_by_period':{str(p):float(Z[0][j]) for j,p in enumerate(PERIODS)},'truth':TRUTH[k]}
print()
for k in out: print(f"  {k:5s} best-p={out[k]['best_p']:2d} p_fw={out[k]['p_familywise']:.4f}   TRUTH: {TRUTH[k]}")
json.dump(out,open('results/pk9_positive_control.json','w'),indent=1)
print(f"\nwall {time.time()-t0:.0f}s")
