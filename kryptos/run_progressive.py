import numpy as np, json, sys
from lib import *
from progressive import progression
TARGET=sys.argv[1]; NSH=int(sys.argv[2])
ct=CT[TARGET]; n=len(ct)
rng=np.random.default_rng(777)
res=[]
for aname,alpha in (('KA',KA),('AZ',AZ)):
    C=to_idx(ct,alpha).astype(np.int64)
    SH=np.array([to_idx(''.join(rng.permutation(list(ct))),alpha) for _ in range(NSH)],dtype=np.int64)
    for kind in ('block','letter','quad'):
        for p in range(1,n//5+1):
            for d in range(0,26):
                if kind=='block' and d==0 and p>1: pass
                g=progression(kind,n,p,d)
                def cstat(M):                     # M: (rows,n) -> mean col-IoC over classes mod p
                    tot=np.zeros(M.shape[0])
                    for r in range(p):
                        R=(M[:,r::p]-g[r::p])%26; L=R.shape[1]
                        if L<4: continue
                        off=(np.arange(R.shape[0])*26)[:,None]
                        cnt=np.bincount((off+R).ravel(),minlength=R.shape[0]*26).reshape(-1,26).astype(float)
                        tot+=(cnt*(cnt-1)).sum(1)/(L*(L-1))
                    return tot/p
                obs=float(cstat(C[None,:])[0]); nv=cstat(SH)
                z=(obs-nv.mean())/nv.std()
                res.append({'alpha':aname,'kind':kind,'p':p,'d':d,'obs':round(obs,5),
                            'z':round(float(z),3),'null_max':round(float(((nv-nv.mean())/nv.std()).max()),3),
                            'eff':int(p*26//np.gcd(d,26)) if d else p})
        print(f"{TARGET} {aname} {kind} done ({len(res)} cells)",flush=True)
json.dump({'target':TARGET,'n':n,'nshuf':NSH,'cells':res},open(f'results/progressive_{TARGET}.json','w'))
res.sort(key=lambda r:-r['z'])
print(f"\n=== {TARGET}: {len(res)} cells ===")
allz=np.array([r['z'] for r in res])
print(f"z distribution: mean {allz.mean():.2f} sd {allz.std():.2f} max {allz.max():.2f}")
print("top 15 cells:")
for r in res[:15]: print("  ",r)
