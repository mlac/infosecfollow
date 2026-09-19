"""Posterior over the EFFECTIVE number of distinct cipher alphabets k, from PK9's IoC;
plus real-dictionary-word keys (which carry repeated letters, so k_eff < key length)."""
import sys, json, time, numpy as np
sys.path.insert(0,'.')
from lib import *
rng=np.random.default_rng(4242); t0=time.time(); n=144; N=20000
CORP=np.concatenate([np.array([AZ.index(c) for c in PT[k]],dtype=np.int64) for k in sorted(PT)])
NC=len(CORP)
def ptwin(N): 
    st=rng.integers(0,NC-n,size=N); return CORP[(st[:,None]+np.arange(n)[None,:])]
def iocs(C):
    cnt=np.zeros((C.shape[0],26),dtype=np.int32)
    for x in range(26): cnt[:,x]=(C==x).sum(1)
    return (cnt.astype(float)*(cnt-1)).sum(1)/(n*(n-1))
c9=np.zeros(26,dtype=np.int64)
for ch in CT['pk9']: c9[AZ.index(ch)]+=1
OBS=float((c9*(c9-1)).sum()/(n*(n-1)))
print(f"PK9 IoC = {OBS:.5f}   chi2_uniform = 26*(n-1)*IoC + 26 - n = {26*143*OBS+26-144:.2f}")

P=ptwin(N)
print("\n=== POSTERIOR over effective alphabet count k (aperiodic, uniform over k shifts) ===")
KS=list(range(1,17))+[20,26,10**6]
L={}
for k in KS:
    if k>=10**6: C=(P+rng.integers(0,26,size=(N,n)))%26; lab='inf (flat key)'
    elif k==1:   C=np.take_along_axis(np.stack([rng.permutation(26) for _ in range(N)]),P,1); lab='1 (mono)'
    else:
        sub=np.stack([rng.permutation(26)[:k] for _ in range(N)])
        C=(P+np.take_along_axis(sub,rng.integers(0,k,size=(N,n)),1))%26; lab=str(k)
    v=iocs(C); m,s=v.mean(),v.std(ddof=1)
    L[k]=(lab,m,s,float(np.exp(-0.5*((OBS-m)/s)**2)/s))
Z=sum(x[3] for x in L.values())
print(f"{'k':>16} {'IoC mean':>9} {'sd':>7} {'z(PK9)':>7} {'rel.likelihood':>14} {'posterior':>10}")
post={}
for k in KS:
    lab,m,s,l=L[k]; print(f"{lab:>16} {m:9.5f} {s:7.5f} {(OBS-m)/s:+7.2f} {l/max(x[3] for x in L.values()):14.4f} {l/Z:10.4f}")
    post[lab]={'ioc_mean':m,'ioc_sd':s,'z':float((OBS-m)/s),'posterior':l/Z}
best=max(L,key=lambda k:L[k][3]); print(f"  MAP k = {L[best][0]}")
cum=0; hpd=[]
for k in sorted(KS,key=lambda k:-L[k][3]):
    cum+=L[k][3]/Z; hpd.append(L[k][0])
    if cum>=0.95: break
print(f"  95% credible set for k: {sorted(hpd,key=lambda s:(s[0].isdigit()==False,s))}")

print("\n=== REAL DICTIONARY-WORD KEYS (repeated letters shrink k_eff) ===")
W=open('words.txt').read().split()
Wi={Lg:[w for w in W if len(w)==Lg] for Lg in range(4,17)}
rows=[]
print(f"{'keylen':>6} {'mean distinct':>13} {'IoC mean':>9} {'sd':>7} {'z(PK9)':>7} {'verdict':>11}")
for Lg in range(4,17):
    ws=[Wi[Lg][i] for i in rng.integers(0,len(Wi[Lg]),N)]
    K=np.array([[AZ.index(c) for c in w] for w in ws])
    nd=np.array([len(set(w)) for w in ws]).mean()
    C=(P+K[:,np.arange(n)%Lg])%26; v=iocs(C); m,s=v.mean(),v.std(ddof=1); z=(OBS-m)/s
    vd='CONSISTENT' if abs(z)<2 else ('excl' if abs(z)<3 else 'EXCLUDED')
    print(f"{Lg:6d} {nd:13.2f} {m:9.5f} {s:7.5f} {z:+7.2f} {vd:>11}")
    rows.append(dict(keylen=Lg,mean_distinct=float(nd),ioc_mean=float(m),ioc_sd=float(s),z=float(z),verdict=vd))
json.dump(dict(obs_ioc=OBS,posterior_k=post,word_keys=rows,nsim=N),
          open('results/pk9_posterior_k.json','w'),indent=1)
print(f"\nsims={len(KS)*N + 13*N}  wall {time.time()-t0:.0f}s")
