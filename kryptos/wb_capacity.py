"""How much information does 'must decompose into dictionary words' carry?
a_n = #letter-strings of length n that are concatenations of vocab words.
Growth rate lambda = a_n^(1/n).  Expected # of DUAL-consistent (pt,key) pairs for a
random n-letter ciphertext = a_pt(n) * a_key(n) / 26^n."""
import sys, numpy as np; sys.path.insert(0,'.')
from math import log10
def counts(minL,maxL,topk=None):
    ws=open('words.txt').read().split()
    if topk: ws=ws[:topk]
    c={}
    for w in ws:
        if minL<=len(w)<=maxL: c[len(w)]=c.get(len(w),0)+1
    return c
def loga(c,n):
    """log10 a_n via DP in log space."""
    NEG=-1e30; L=np.full(n+1,NEG); L[0]=0.0
    lc={k:log10(v) for k,v in c.items()}
    for i in range(1,n+1):
        terms=[L[i-k]+lc[k] for k in c if i-k>=0 and L[i-k]>NEG/2]
        if not terms: continue
        m=max(terms); L[i]=m+log10(sum(10**(t-m) for t in terms))
    return L
n=504
cfgs=[('pt full 3-16',dict(minL=3,maxL=16)),
      ('len>=4',dict(minL=4,maxL=16)),('len>=5',dict(minL=5,maxL=16)),
      ('len>=6',dict(minL=6,maxL=16)),('len>=7',dict(minL=7,maxL=16)),
      ('len>=8',dict(minL=8,maxL=16)),('len>=9',dict(minL=9,maxL=16)),
      ('len>=10',dict(minL=10,maxL=16)),
      ('top20k 3-16',dict(minL=3,maxL=16,topk=20000)),
      ('top5k 3-16',dict(minL=5000 and 3,maxL=16,topk=5000)),
      ]
res={}
for name,kw in cfgs:
    c=counts(**kw); L=loga(c,n); lam=10**(L[n]/n)
    res[name]=(L[n],lam,sum(c.values()))
    print(f"{name:16s} words={sum(c.values()):7d}  log10 a_504={L[n]:9.1f}  lambda={lam:6.3f}")
print()
print("log10 26^504 =", 504*log10(26))
print("\nExpected # dual-consistent (pt,key) pairs, log10  =  log10 a_pt + log10 a_key - 504*log10(26)")
base=504*log10(26)
for pn,(pl,plam,_) in res.items():
    row=[]
    for kn,(kl,klam,_) in res.items():
        row.append(f"{kn}:{pl+kl-base:+9.1f}")
    print(f"  pt={pn:16s} " + '  '.join(row[:6]))
