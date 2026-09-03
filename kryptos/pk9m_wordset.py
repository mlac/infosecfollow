"""ATTACK implied by the finding: if PK9's keystream uses only ~4-6 distinct letters in an
aperiodic order, the natural setter-grammar source is 'the letters of one thematic word, used in
an unpredictable order'.  That is a 289k-word hypothesis test on the CENSUS ALONE -- it needs no
period, survives any transposition, and survives any order of the key letters.

Model: q = uniform on the distinct letters of word w (as shifts).  Census log-likelihood
LL(w) = sum_c cnt_c * log( mean_{s in S_w} pPT[(c-s) mod 26] ).  Score = LL(w) - LL(uniform q).
Matched null: the IDENTICAL 289k-word search run on simulated ciphertexts of the same length.
Positive controls: PK1 (true key PROVENANCE) and PK6 (true key PORTAL), both Q3 on KA."""
import sys, json, time, numpy as np
sys.path.insert(0,'.')
from lib import *
rng=np.random.default_rng(9001); t0=time.time()
ENG=np.array([8.167,1.492,2.782,4.253,12.702,2.228,2.015,6.094,6.966,0.153,0.772,4.025,2.406,
              6.749,7.507,1.929,0.095,5.987,6.327,9.056,2.758,0.978,2.360,0.150,1.974,0.074]); ENG/=ENG.sum()
PRIOR={'AZ':ENG.copy(), 'KA':np.array([ENG[AZI[KA[j]]] for j in range(26)])}
CORP=np.concatenate([np.array([AZI[c] for c in PT[q]],dtype=np.int64) for q in sorted(PT)])

W=[w for w in open('words.txt').read().split() if 3<=len(w)<=12]
print(f"words: {len(W)}")
IND={}
for lab in ('AZ','KA'):
    A=lab=='AZ' and AZI or KAI
    M=np.zeros((len(W),26),dtype=np.float32)
    for i,w in enumerate(W):
        s=set(A[c] for c in w); M[i,list(s)]=1.0/len(s)
    IND[lab]=M
NDIST=np.array([len(set(w)) for w in W])

def mixmat(lab):
    pr=PRIOR[lab]; SH=np.stack([np.roll(pr,s) for s in range(26)])   # (s,c)
    return IND[lab]@SH                                               # (Nw,26) mixture over c
MIX={lab:np.log(np.maximum(mixmat(lab),1e-12)) for lab in ('AZ','KA')}
UNI={lab:np.log(np.full(26,1/26.)) for lab in ('AZ','KA')}

def scores(cnt,lab):
    return MIX[lab]@cnt - float(cnt.sum())*np.log(1/26.)
def cens(s,alpha):
    a={c:i for i,c in enumerate(alpha)}; c=np.zeros(26)
    for ch in s: c[a[ch]]+=1
    return c

print("\n=== POSITIVE CONTROLS on solved ciphertexts (true key known) ===")
for k,truth in [('pk1','PROVENANCE'),('pk6','PORTAL'),('pk3','PENTIMENTO'),('pk4','VERDIGRIS')]:
    for lab in ('KA',):
        sc=scores(cens(CT[k],KA),lab); o=np.argsort(sc)[::-1]
        r=W.index(truth) if truth in W else None
        rank=int((sc>sc[r]).sum())+1 if r is not None else None
        print(f"  {k} (n={len(CT[k])}) true={truth:11s} rank={rank}/{len(W)}  score={sc[r]:.2f}"
              f"   top5: "+", ".join(f"{W[j]}({sc[j]:.1f})" for j in o[:5]))

print("\n=== MATCHED NULL: same 289k-word search on simulated ciphertexts, n=144 ===")
NN=300; n=144
def ptw(N):
    st=rng.integers(0,len(CORP)-n,size=N); return CORP[(st[:,None]+np.arange(n)[None,:])]
nullmax={}
for lab in ('AZ','KA'):
    P=ptw(NN); mx=np.zeros(NN)
    for i in range(NN):
        C=(P[i]+rng.integers(0,26,n))%26
        c=np.bincount(C,minlength=26).astype(float)
        mx[i]=scores(c,lab).max()
    nullmax[lab]=mx
    print(f"  {lab} flat-key null: max-score mean {mx.mean():.2f} sd {mx.std(ddof=1):.2f}"
          f" 95th {np.percentile(mx,95):.2f} MAX {mx.max():.2f}")
# a second null: k=5-alphabet ciphertexts whose key letters are NOT a word
for lab in ('KA',):
    P=ptw(NN); mx=np.zeros(NN)
    for i in range(NN):
        S=rng.permutation(26)[:5]; C=(P[i]+S[rng.integers(0,5,n)])%26
        mx[i]=scores(np.bincount(C,minlength=26).astype(float),lab).max()
    print(f"  {lab} random-5-alphabet null: max mean {mx.mean():.2f} sd {mx.std(ddof=1):.2f} MAX {mx.max():.2f}")
    nullmax[lab+'_k5']=mx

print("\n=== PK8 / PK9 / PK10 ===")
res={}
for k in ('pk8','pk9','pk10'):
    for lab in ('AZ','KA'):
        alpha=AZ if lab=='AZ' else KA
        sc=scores(cens(CT[k],alpha),lab); o=np.argsort(sc)[::-1]
        nm=nullmax[lab] if k=='pk9' else nullmax[lab]
        z=(sc.max()-nm.mean())/nm.std(ddof=1)
        flag='ABOVE NULL MAX' if sc.max()>nm.max() else 'below ceiling'
        print(f"  {k} {lab}: best={sc.max():.2f} z={z:+.2f} [{flag}]  top8: "
              +", ".join(f"{W[j]}({sc[j]:.1f},d={NDIST[j]})" for j in o[:8]))
        res[f'{k}_{lab}']={'best':float(sc.max()),'z_vs_null':float(z),
            'null_mean':float(nm.mean()),'null_sd':float(nm.std(ddof=1)),'null_max':float(nm.max()),
            'above_ceiling':bool(sc.max()>nm.max()),
            'top20':[[W[int(j)],float(sc[j]),int(NDIST[j])] for j in o[:20]]}
json.dump(dict(nwords=len(W),nnull=NN,res=res),open('results/pk9_wordset.json','w'),indent=1)
print(f"\nwall {time.time()-t0:.0f}s ; word-hypotheses tested = {len(W)*2*3 + len(W)*NN*3}")
