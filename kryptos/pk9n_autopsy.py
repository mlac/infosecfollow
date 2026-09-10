"""AUTOPSY of pk9-KA word-set score 14.50 (CADDY/CADY/CYCAD, 4 distinct letters).
The flat-key null is NOT matched: the word-set score is a pure CENSUS statistic, and PK9's census
is more concentrated than a flat key's (IoC z=+3.2).  The matched null must generate ciphertexts
with the SAME census concentration by a NON-WORD mechanism.  Two matched nulls are built:
 (N1) k-alphabet ciphertexts, shift set = a random k-subset of the alphabet (not a word);
 (N2) the same, rejection-sampled to |IoC - IoC(PK9)| < 0.0015 -- the tightest possible match.
A shuffle null is impossible here: the statistic is census-only, so every permutation of PK9
scores exactly 14.50 (variance zero). Recorded as such."""
import sys, json, time, numpy as np
sys.path.insert(0,'.')
from lib import *
rng=np.random.default_rng(555); t0=time.time(); n=144
ENG=np.array([8.167,1.492,2.782,4.253,12.702,2.228,2.015,6.094,6.966,0.153,0.772,4.025,2.406,
              6.749,7.507,1.929,0.095,5.987,6.327,9.056,2.758,0.978,2.360,0.150,1.974,0.074]); ENG/=ENG.sum()
PRIOR_KA=np.array([ENG[AZI[KA[j]]] for j in range(26)])
CORP=np.concatenate([np.array([AZI[c] for c in PT[q]],dtype=np.int64) for q in sorted(PT)])
W=[w for w in open('words.txt').read().split() if 3<=len(w)<=12]
M=np.zeros((len(W),26),dtype=np.float32)
for i,w in enumerate(W):
    s=set(KAI[c] for c in w); M[i,list(s)]=1.0/len(s)
SH=np.stack([np.roll(PRIOR_KA,s) for s in range(26)])
LOGMIX=np.log(np.maximum(M@SH,1e-12)).astype(np.float64)
def sc(cnt): return LOGMIX@cnt - float(cnt.sum())*np.log(1/26.)
c9=np.zeros(26)
for ch in CT['pk9']: c9[KAI[ch]]+=1
S9=sc(c9); OBS=float(S9.max()); ioc9=float((c9*(c9-1)).sum()/(n*143))
print(f"PK9 KA: observed best word-set score {OBS:.3f}, IoC {ioc9:.5f}")
o=np.argsort(S9)[::-1]
print("  top 12:", ", ".join(f"{W[j]}({S9[j]:.2f})" for j in o[:12]))
print("  NOTE: this statistic is a function of the CENSUS ALONE -> every one of the 144! "
      "permutations of PK9 scores exactly 14.50. A shuffle null has zero variance and is useless.")
# PK9's own maximum-likelihood shift set (unrestricted 4-subset) -- the ceiling any word can reach
from itertools import combinations
best4=-1e9; arg=None
for S in combinations(range(26),4):
    m=SH[list(S)].mean(0); v=float((c9*np.log(m)).sum()-144*np.log(1/26.))
    if v>best4: best4,arg=v,S
print(f"  unrestricted best 4-subset: {''.join(KA[i] for i in arg)} score {best4:.2f} "
      f"(the winning WORD reaches {OBS:.2f} of that)")

def ptw(N):
    st=rng.integers(0,len(CORP)-n,size=N); return CORP[(st[:,None]+np.arange(n)[None,:])]
def run_null(k,NN,match_ioc=False,tol=0.0015):
    mx=[]; tries=0
    while len(mx)<NN:
        tries+=1
        P=ptw(1)[0]; S=rng.permutation(26)[:k]
        C=(P+S[rng.integers(0,k,n)])%26
        c=np.bincount(C,minlength=26).astype(float)
        if match_ioc and abs((c*(c-1)).sum()/(n*143)-ioc9)>tol: continue
        mx.append(float(sc(c).max()))
    return np.array(mx),tries
res={'obs':OBS,'top20':[[W[int(j)],float(S9[j])] for j in o[:20]],
     'unrestricted_best4':{'set':''.join(KA[i] for i in arg),'score':best4},
     'shuffle_null':'zero variance -- statistic is census-only','nulls':{}}
print(f"\n{'matched null':38s} {'N':>5} {'mean':>7} {'sd':>6} {'95th':>7} {'MAX':>7} {'z':>6} {'p_emp':>6}")
for k in [3,4,5,6]:
    for mi in (False,True):
        NN=1200
        mx,tr=run_null(k,NN,mi)
        z=(OBS-mx.mean())/mx.std(ddof=1); pe=float((mx>=OBS).mean())
        lab=f"N{'2' if mi else '1'}: random {k}-letter shift set"+(" | IoC matched" if mi else "")
        print(f"{lab:38s} {NN:5d} {mx.mean():7.2f} {mx.std(ddof=1):6.2f} "
              f"{np.percentile(mx,95):7.2f} {mx.max():7.2f} {z:+6.2f} {pe:6.3f}")
        res['nulls'][lab]={'N':NN,'mean':float(mx.mean()),'sd':float(mx.std(ddof=1)),
            'p95':float(np.percentile(mx,95)),'max':float(mx.max()),'z':float(z),'p_emp':pe,
            'above_ceiling':bool(OBS>mx.max())}
json.dump(res,open('results/pk9_wordset_autopsy.json','w'),indent=1)
print(f"\nwall {time.time()-t0:.0f}s")
