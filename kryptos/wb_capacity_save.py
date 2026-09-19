import sys, json, numpy as np; sys.path.insert(0,'.')
from math import log10
def counts(minL,maxL=16,topk=None):
    ws=open('words.txt').read().split()
    if topk: ws=ws[:topk]
    c={}
    for w in ws:
        if minL<=len(w)<=maxL: c[len(w)]=c.get(len(w),0)+1
    return c
def loga(c,n):
    NEG=-1e30; L=np.full(n+1,NEG); L[0]=0.0
    lc={k:log10(v) for k,v in c.items()}
    for i in range(1,n+1):
        t=[L[i-k]+lc[k] for k in c if i-k>=0 and L[i-k]>NEG/2]
        if not t: continue
        m=max(t); L[i]=m+log10(sum(10**(x-m) for x in t))
    return L[n]
n=504; base=n*log10(26)
res={'n':n,'log10_26^n':round(base,2),'vocab':{}}
for m in (3,4,5,6,7,8,9,10,11,12):
    c=counts(m); la=loga(c,n)
    res['vocab'][f'len>={m}']={'words':sum(c.values()),'log10_a_n':round(la,2),
                               'lambda':round(10**(la/n),4)}
pt=res['vocab']['len>=3']['log10_a_n']
res['expected_dual_solutions_log10_ptfull']={
    k: round(pt+v['log10_a_n']-base,1) for k,v in res['vocab'].items()}
res['note']=("a_n = number of letter strings of length n that concatenate dictionary words. "
             "Expected number of (plaintext,key) pairs BOTH word-decomposable and consistent "
             "with a random n-letter ciphertext = a_pt(n)*a_key(n)/26^n. With a realistic "
             "plaintext vocabulary (len>=3, needed to cover real English) every key vocabulary "
             "leaves 10^200..10^667 consistent pairs, so the word constraint ALONE carries no "
             "identifying information at n=504; all identification must come from the language "
             "model, and a quadgram model is degenerate (THE-repeated scores -2.64/letter vs "
             "English -4.25/letter).")
json.dump(res,open('results/wb_capacity.json','w'),indent=1)
print(json.dumps(res['vocab'],indent=1))
print(json.dumps(res['expected_dual_solutions_log10_ptfull'],indent=1))
