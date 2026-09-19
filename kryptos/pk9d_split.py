"""PK9: is the IoC excess LOCALIZED in position? Changepoint / trend / block families,
each with a familywise-corrected matched null (random permutations of PK9)."""
import sys, json, time, numpy as np
sys.path.insert(0,'.')
from lib import *
rng=np.random.default_rng(7); t0=time.time()
def idx(s): return np.array([AZ.index(c) for c in s],dtype=np.int64)
C9=idx(CT['pk9']); n=144
NSH=20000
SH=np.stack([rng.permutation(C9) for _ in range(NSH)])
ALL=np.vstack([C9[None,:],SH])          # row 0 = real

def seg_ioc(A,a,b):
    sub=A[:,a:b]; L=b-a
    cnt=np.zeros((A.shape[0],26),dtype=np.int32)
    for x in range(26): cnt[:,x]=(sub==x).sum(1)
    return (cnt*(cnt-1)).sum(1)/(L*(L-1))

res={}
def report(name,stat):
    obs=stat[0]; nul=stat[1:]
    m,s=nul.mean(),nul.std(ddof=1); z=(obs-m)/s; pe=float((nul>=obs).mean())
    print(f"  {name:34s} obs={obs:9.5f} null={m:8.5f}+-{s:.5f} z={z:+6.2f} p_emp={pe:.4f} nullmax={nul.max():.5f}")
    res[name]={'obs':float(obs),'null_mean':float(m),'null_sd':float(s),'z':float(z),
               'p_emp':pe,'null_max':float(nul.max())}
    return pe

print("=== FAMILY B: contiguous blocks, mean per-block IoC, familywise max-z ===")
KS=[2,3,4,6,8,9,12,16]
Zb=np.zeros((NSH+1,len(KS)))
for j,k in enumerate(KS):
    b=n//k
    v=sum(seg_ioc(ALL,i*b,(i+1)*b) for i in range(k))/k
    nul=v[1:]; Zb[:,j]=(v-nul.mean())/nul.std(ddof=1)
    print(f"   k={k:2d} obs={v[0]:.5f} z={Zb[0,j]:+.2f}")
pB=report("B: max-z over 8 block splits",np.max(Zb,1))

print("\n=== FAMILY C: changepoint, max |IoC(0:s) - IoC(s:n)| over s=24..120 ===")
SS=list(range(24,121,4))
D=np.zeros((NSH+1,len(SS)))
for j,s in enumerate(SS): D[:,j]=np.abs(seg_ioc(ALL,0,s)-seg_ioc(ALL,s,n))
best=int(np.argmax(D[0])); print(f"   best split s={SS[best]}  |delta|={D[0,best]:.5f}"
      f"  left={seg_ioc(ALL[:1],0,SS[best])[0]:.5f} right={seg_ioc(ALL[:1],SS[best],n)[0]:.5f}")
pC=report("C: max |delta IoC| over 25 splits",np.max(D,1))
# signed version: right minus left
Dg=np.zeros((NSH+1,len(SS)))
for j,s in enumerate(SS): Dg[:,j]=seg_ioc(ALL,s,n)-seg_ioc(ALL,0,s)
pC2=report("C2: max (right-left) signed",np.max(Dg,1))

print("\n=== FAMILY D: monotone trend in local IoC (windows w=36, step 4) ===")
W=36; starts=list(range(0,n-W+1,4))
Vw=np.stack([seg_ioc(ALL,s,s+W) for s in starts],1)   # (N, nwin)
rk=np.argsort(np.argsort(Vw,axis=1),axis=1).astype(float)
xx=np.arange(len(starts)); xx=(xx-xx.mean())/xx.std()
rr=(rk-rk.mean(1,keepdims=True)); rr/=rr.std(1,keepdims=True)
sp=(rr*xx).mean(1)
pD=report("D: Spearman(window index, IoC)",sp)

print("\n=== FAMILY E: fixed a-priori halves/thirds (single tests) ===")
pE1=report("E1: IoC(last 72) - IoC(first 72)",seg_ioc(ALL,72,n)-seg_ioc(ALL,0,72))
pE2=report("E2: IoC(middle third 48:96)",seg_ioc(ALL,48,96))

print("\n=== GLOBAL FAMILYWISE over families {A residue, B block, C changepoint, D trend} ===")
# rebuild A on same shuffles
def classioc(A,p):
    out=np.zeros(A.shape[0])
    for r in range(p):
        sub=A[:,r::p]; L=sub.shape[1]
        cnt=np.zeros((A.shape[0],26),dtype=np.int32)
        for x in range(26): cnt[:,x]=(sub==x).sum(1)
        out+=(cnt*(cnt-1)).sum(1)/(L*(L-1))
    return out/p
Za=np.zeros((NSH+1,11))
for j,p in enumerate(range(2,13)):
    v=classioc(ALL,p); nul=v[1:]; Za[:,j]=(v-nul.mean())/nul.std(ddof=1)
def zof(M):
    nul=M[1:]; return (M-nul.mean())/nul.std(ddof=1)
G=np.column_stack([np.max(Za,1),np.max(Zb,1),zof(np.max(D,1)),zof(sp)])
Gz=np.column_stack([zof(G[:,i]) for i in range(4)])
gm=np.max(Gz,1); nul=gm[1:]
print(f"  observed global max-z = {gm[0]:+.2f}; null max-z mean {nul.mean():.2f} sd {nul.std(ddof=1):.2f}"
      f" 95th {np.percentile(nul,95):.2f} max {nul.max():.2f}  p_emp={float((nul>=gm[0]).mean()):.4f}")
res['GLOBAL']={'obs':float(gm[0]),'null_mean':float(nul.mean()),'null_95':float(np.percentile(nul,95)),
               'null_max':float(nul.max()),'p_emp':float((nul>=gm[0]).mean()),
               'families':['residue2-12','block','changepoint','trend']}
json.dump(res,open('results/pk9_split.json','w'),indent=1)
print(f"wall {time.time()-t0:.0f}s")
