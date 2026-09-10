"""PK9 construction likelihood table. Simulate each candidate construction at n=144 with the
setter's own English as plaintext, and report the distribution of the census statistics.
IoC, chi2-vs-uniform, chi2-vs-English are the deliverable; all are census (permutation-invariant)
statistics, so they are unaffected by any transposition layer."""
import sys, json, time, numpy as np
sys.path.insert(0,'.')
from lib import *
rng=np.random.default_rng(11); t0=time.time()
N=6000; n=144

ENG=np.array([8.167,1.492,2.782,4.253,12.702,2.228,2.015,6.094,6.966,0.153,0.772,4.025,2.406,
              6.749,7.507,1.929,0.095,5.987,6.327,9.056,2.758,0.978,2.360,0.150,1.974,0.074])
ENG=ENG/ENG.sum()
CONV=np.array([sum(ENG[a]*ENG[(c-a)%26] for a in range(26)) for c in range(26)])
LOGR=np.log(CONV*26.0)                      # running-key vs flat log-lik ratio weights

CORP=np.concatenate([np.array([AZ.index(c) for c in PT[k]],dtype=np.int64) for k in sorted(PT)])
NC=len(CORP)
def ptwin(N,n):                              # N random windows of the setter's own plaintext
    st=rng.integers(0,NC-n,size=N)
    return CORP[(st[:,None]+np.arange(n)[None,:])]

def stats(C):
    cnt=np.zeros((C.shape[0],26),dtype=np.int32)
    for x in range(26): cnt[:,x]=(C==x).sum(1)
    s2=(cnt.astype(np.float64)*(cnt-1)).sum(1)
    ioc=s2/(n*(n-1)); chi2u=26*(n-1)*ioc+26-n
    o=np.sort(cnt,1)[:,::-1]; e=n*np.sort(ENG)[::-1]
    ces=(((o-e)**2)/e).sum(1)
    llr=(cnt*LOGR).sum(1)
    return dict(ioc=ioc,chi2u=chi2u,ces=ces,mx=cnt.max(1).astype(float),
                mn=cnt.min(1).astype(float),llr=llr)

def perm_alpha(N):
    return np.stack([rng.permutation(26) for _ in range(N)])

H={}
P=ptwin(N,n)
H['plaintext (or pure transposition)']=P.copy()
A=perm_alpha(N); H['monoalphabetic (keyed alphabet)']=np.take_along_axis(A,P,1)
H['flat/random long key (one-time)']=(P+rng.integers(0,26,size=(N,n)))%26
for p in list(range(2,15)):
    k=rng.integers(0,26,size=(N,p)); H[f'periodic p={p} (key letters iid)']=(P+k[:,np.arange(n)%p])%26
for p in [2,3,4,5,6,7,8]:
    k=np.stack([rng.permutation(26)[:p] for _ in range(N)])
    H[f'periodic p={p} (DISTINCT key letters)']=(P+k[:,np.arange(n)%p])%26
for k_ in range(2,11):
    sub=np.stack([rng.permutation(26)[:k_] for _ in range(N)])
    pick=rng.integers(0,k_,size=(N,n))
    H[f'APERIODIC, {k_} distinct alphabets']=(P+np.take_along_axis(sub,pick,1))%26
for Pp in [9,12,16,18,24,36,48,72,144]:
    for k_ in [3,4,5]:
        sub=np.stack([rng.permutation(26)[:k_] for _ in range(N)])
        key=np.take_along_axis(sub,rng.integers(0,k_,size=(N,Pp)),1)
        H[f'period {Pp} key, only {k_} distinct letters']=(P+key[:,np.arange(n)%Pp])%26
K=ptwin(N,n); H['running key, same alphabet']=(P+K)%26
A=perm_alpha(N); H['running key thru independent keyed alphabet']=(P+np.take_along_axis(A,K,1))%26
pr=rng.integers(0,26,size=(N,8)); AK=np.concatenate([pr,P[:,:n-8]],1); H['plaintext autokey (primer 8)']=(P+AK)%26
C=np.zeros((N,n),dtype=np.int64); C[:,:8]=(P[:,:8]+pr)%26
for i in range(8,n): C[:,i]=(P[:,i]+C[:,i-8])%26
H['ciphertext autokey (primer 8)']=C
def hill(P,k,cond):
    N_=P.shape[0]; out=np.zeros_like(P)
    M=np.zeros((N_,k,k),dtype=np.int64)
    for i in range(N_):
        while True:
            m=rng.integers(0,26,size=(k,k)); d=int(round(np.linalg.det(m)))%26
            if cond(d): break
        M[i]=m
    B=P[:,:(n//k)*k].reshape(N_,-1,k)
    R=np.einsum('nij,nbj->nbi',M,B)%26
    out[:,:(n//k)*k]=R.reshape(N_,-1); return out
from math import gcd
Nh=1500
Ph=P[:Nh]
H['Hill 2x2 invertible']=hill(Ph,2,lambda d: gcd(d,26)==1)
H['Hill 3x3 invertible']=hill(Ph,3,lambda d: gcd(d,26)==1)
H['Hill 2x2 RANK-DEFICIENT (det=0 mod 26)']=hill(Ph,2,lambda d: d==0)
H['Hill 2x2 det=0 mod 13 only']=hill(Ph,2,lambda d: d%13==0 and d%2==1)
a=rng.integers(0,26,size=(N,1)); m=(P*0+1)
H['split: 1st half mono, 2nd half flat']=np.concatenate(
    [np.take_along_axis(perm_alpha(N),P[:,:72],1),(P[:,72:]+rng.integers(0,26,size=(N,72)))%26],1)
H['split: 1st half monoA, 2nd half monoB']=np.concatenate(
    [np.take_along_axis(perm_alpha(N),P[:,:72],1),np.take_along_axis(perm_alpha(N),P[:,72:],1)],1)
k4=rng.integers(0,26,size=(N,4))
H['split: 1st half p=4, 2nd half flat']=np.concatenate(
    [(P[:,:72]+k4[:,np.arange(72)%4])%26,(P[:,72:]+rng.integers(0,26,size=(N,72)))%26],1)
W=[w for w in open('words.txt').read().split() if 3<=len(w)<=12]
Wi={L:[w for w in W if len(w)==L] for L in range(3,13)}
def prodkey(a_,b_,N_):
    wa=[Wi[a_][i] for i in rng.integers(0,len(Wi[a_]),N_)]
    wb=[Wi[b_][i] for i in rng.integers(0,len(Wi[b_]),N_)]
    ka=np.array([[AZ.index(c) for c in w] for w in wa]); kb=np.array([[AZ.index(c) for c in w] for w in wb])
    ii=np.arange(n); return (ka[:,ii%a_]+kb[:,ii%b_])%26
for (a_,b_) in [(5,9),(10,8),(4,9),(6,7),(7,12)]:
    H[f'two-word product key ({a_},{b_}) lcm={np.lcm(a_,b_)}']=(P+prodkey(a_,b_,N))%26
st=rng.integers(0,26,size=(N,1)); inc=rng.integers(1,26,size=(N,1))
blk=np.arange(n)//9
H['progressive key (+d per 9-block)']=(P+(st+inc*blk[None,:]))%26
A=perm_alpha(N); k4b=rng.integers(0,26,size=(N,4))
H['mono applied ON TOP of periodic p=4']=np.take_along_axis(A,(P+k4b[:,np.arange(n)%4])%26,1)
A=perm_alpha(N)
H['Quagmire-III style: keyed alpha, period 6']=np.take_along_axis(A,(np.take_along_axis(
    np.argsort(A,1),P,1)+rng.integers(0,26,size=(N,6))[:,np.arange(n)%6])%26,1)

OBS=dict(ioc=0.04450, chi2u=47.39, ces=52.83, mx=13.0, mn=1.0, llr=None)
c9=np.zeros(26,dtype=np.int64)
for ch in CT['pk9']: c9[AZ.index(ch)]+=1
OBS['ioc']=float((c9*(c9-1)).sum()/(n*(n-1))); OBS['chi2u']=26*(n-1)*OBS['ioc']+26-n
OBS['ces']=float((((np.sort(c9)[::-1]-n*np.sort(ENG)[::-1])**2)/(n*np.sort(ENG)[::-1])).sum())
OBS['llr']=float((c9*LOGR).sum())
print("PK9 observed:", {k:round(v,4) for k,v in OBS.items()})

rows=[]
print(f"\n{'construction':46s} {'nsim':>5} {'IoC mean':>9} {'sd':>7} {'z(PK9)':>7} {'chi2u':>7} "
      f"{'ces/n':>6} {'maxct':>6} {'LLR z':>7} {'verdict':>10}")
for name,Cx in H.items():
    s=stats(Cx); ns=Cx.shape[0]
    z=(OBS['ioc']-s['ioc'].mean())/s['ioc'].std(ddof=1)
    zl=(OBS['llr']-s['llr'].mean())/s['llr'].std(ddof=1)
    zc=(OBS['ces']-s['ces'].mean())/s['ces'].std(ddof=1)
    zm=(OBS['mx']-s['mx'].mean())/s['mx'].std(ddof=1)
    v='CONSISTENT' if abs(z)<2 else ('excl' if abs(z)<3 else 'EXCLUDED')
    print(f"{name:46s} {ns:5d} {s['ioc'].mean():9.5f} {s['ioc'].std(ddof=1):7.5f} {z:+7.2f} "
          f"{s['chi2u'].mean():7.1f} {s['ces'].mean()/n:6.2f} {s['mx'].mean():6.2f} {zl:+7.2f} {v:>10}")
    rows.append(dict(name=name,nsim=int(ns),ioc_mean=float(s['ioc'].mean()),ioc_sd=float(s['ioc'].std(ddof=1)),
        z_ioc=float(z),chi2u_mean=float(s['chi2u'].mean()),chi2u_sd=float(s['chi2u'].std(ddof=1)),
        ces_mean=float(s['ces'].mean()),ces_sd=float(s['ces'].std(ddof=1)),z_ces=float(zc),
        maxct_mean=float(s['mx'].mean()),z_maxct=float(zm),
        llr_mean=float(s['llr'].mean()),llr_sd=float(s['llr'].std(ddof=1)),z_llr=float(zl),
        p_ioc_ge=float((s['ioc']>=OBS['ioc']).mean()),verdict=v))
json.dump(dict(observed=OBS,n=n,rows=rows),open('results/pk9_likelihood.json','w'),indent=1)
print(f"\nHYPOTHESES={len(H)}  total sims={sum(v.shape[0] for v in H.values())}  wall {time.time()-t0:.0f}s")
