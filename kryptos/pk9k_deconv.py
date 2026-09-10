"""PK9 keystream deconvolution.  If the ciphertext census = English census CONVOLVED with the
keystream's shift distribution q, then q can be estimated from the census by EM.  A keystream
using only k distinct letters gives a SPARSE q; a flat/long key gives a uniform q.
Statistic: concentration Sq2 = sum_s q^2 (uniform = 1/26 = .0385).  Matched null = simulated
ciphertexts under the flat-key hypothesis at n=144 from the setter's own plaintext.
CAVEAT recorded up front: this assumes the plaintext is read in the SAME alphabet as the shifts
(true for PK1/PK3/PK4/PK6 Q3 constructions on KA); an independent keyed cipher alphabet breaks it."""
import sys, json, time, numpy as np
sys.path.insert(0,'.')
from lib import *
rng=np.random.default_rng(2718); t0=time.time(); n=144
ENG=np.array([8.167,1.492,2.782,4.253,12.702,2.228,2.015,6.094,6.966,0.153,0.772,4.025,2.406,
              6.749,7.507,1.929,0.095,5.987,6.327,9.056,2.758,0.978,2.360,0.150,1.974,0.074]); ENG/=ENG.sum()
CORP=np.concatenate([np.array([AZ.index(c) for c in PT[q]],dtype=np.int64) for q in sorted(PT)])
def ptwin(N):
    st=rng.integers(0,len(CORP)-n,size=N); return CORP[(st[:,None]+np.arange(n)[None,:])]
SHIFT=np.stack([np.roll(ENG,s) for s in range(26)])          # SHIFT[s,c] = P(c | shift s)

def em(cnt,iters=400):
    """cnt (N,26) -> q (N,26) MLE mixture weights over the 26 shifts"""
    N=cnt.shape[0]; q=np.full((N,26),1/26.)
    for _ in range(iters):
        num=q[:,:,None]*SHIFT[None,:,:]                       # (N,s,c)
        den=num.sum(1,keepdims=True); den[den<1e-300]=1e-300
        r=num/den
        q=(r*cnt[:,None,:]).sum(2)/cnt.sum(1)[:,None]
    return q
def census(C):
    out=np.zeros((C.shape[0],26),dtype=np.int64)
    for x in range(26): out[:,x]=(C==x).sum(1)
    return out
def Sq2(q): return (q**2).sum(1)

print("=== A. THEOREM CHECK: the unconstrained partition search is a permutation invariant ===")
print("    (pk9j_partition.py: PK9 best == shuffle-null MAX at k=2,3,4 to 4 decimals -> the")
print("     objective depends on the census only, so that route has provably zero power.)")

print("\n=== B. POSITIVE CONTROL: can EM recover a KNOWN sparse keystream at n=144? ===")
for k in [2,3,4,5,6]:
    P=ptwin(400); hit=0; rec=[]
    for i in range(400):
        S=rng.permutation(26)[:k]
        C=(P[i]+S[rng.integers(0,k,n)])%26
        q=em(census(C[None,:]))[0]
        top=np.argsort(q)[::-1][:k]
        hit+=len(set(top.tolist())&set(S.tolist()))/k
        rec.append(Sq2(q[None,:])[0])
    print(f"  true k={k}: mean fraction of the true shift-set in the top-{k} of qhat = {hit/400:.3f}"
          f"   (chance {k/26:.3f});  mean Sq2 = {np.mean(rec):.4f}  (true {1/k:.4f})")

print("\n=== C. NULL: flat/long-key ciphertexts at n=144 ===")
Pn=ptwin(3000); Cn=(Pn+rng.integers(0,26,size=(3000,n)))%26
qn=em(census(Cn)); sn=Sq2(qn)
print(f"  flat-key null:  Sq2 mean {sn.mean():.4f}  sd {sn.std(ddof=1):.4f}  95th {np.percentile(sn,95):.4f}  max {sn.max():.4f}")

print("\n=== D. PK9 ===")
out={}
for lab,alpha in [('AZ',AZ),('KA',KA)]:
    c=np.zeros((1,26),dtype=np.int64)
    for ch in CT['pk9']: c[0,alpha.index(ch)]+=1
    q=em(c)[0]; s=float(Sq2(q[None,:])[0]); z=(s-sn.mean())/sn.std(ddof=1)
    top=np.argsort(q)[::-1]
    print(f"  {lab}: Sq2={s:.4f}  z_vs_flat_null={z:+.2f}  p_emp={float((sn>=s).mean()):.4f}")
    print(f"      qhat support (shift letters, weight): "+
          " ".join(f"{alpha[t]}:{q[t]:.3f}" for t in top[:8] if q[t]>0.02))
    print(f"      nonzero shifts: {int((q>0.01).sum())} of 26")
    out[lab]={'Sq2':s,'z':float(z),'p_emp':float((sn>=s).mean()),
              'top':[[alpha[int(t)],float(q[t])] for t in top[:10]],'nnz':int((q>0.01).sum())}
# same treatment for the solved siblings, as calibration
print("\n=== E. CALIBRATION on solved ciphertexts (known keystreams, KA alphabet) ===")
for k in ['pk1','pk6','pk5','pk3']:
    s_=CT[k]; m=len(s_); c=np.zeros((1,26),dtype=np.int64)
    for ch in s_: c[0,KA.index(ch)]+=1
    q=em(c)[0]; top=np.argsort(q)[::-1]
    print(f"  {k} (n={m}): Sq2={float(Sq2(q[None,:])[0]):.4f}  top shifts "+
          " ".join(f"{KA[t]}:{q[t]:.2f}" for t in top[:6] if q[t]>0.03))
print("     PK1 true key PROVENANCE -> shift multiset P,R,O,V,E,E,N,N,A,C ; PK6 true key PORTAL")
json.dump(dict(pk9=out,null_mean=float(sn.mean()),null_sd=float(sn.std(ddof=1)),
               null_95=float(np.percentile(sn,95)),null_max=float(sn.max()),nnull=3000),
          open('results/pk9_deconv.json','w'),indent=1)
print(f"\nwall {time.time()-t0:.0f}s")
