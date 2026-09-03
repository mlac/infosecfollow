"""How many distinct keystream values is each target's own IoC consistent with?

Companion to smallmod_census.py: same forward simulation, m swept 2..26 on both recurrences, to
give a two-sided consistency interval on m per target.  IoC is permutation-invariant, so the result
holds with or without a columnar underneath -- the transposition literally cannot move it.
"""
import numpy as np, json
from lib import KA, CT, PT, to_idx, to_str, ioc, col_enc
DS  = [d for d in range(1,26) if np.gcd(d,26)==1]
SRC = ''.join(PT[k] for k in ('pk2','pk3','pk5','pk6','pk7','pk4','pk1'))
OBS = {t: ioc(CT[t]) for t in ('pk8','pk9','pk10')}
NS  = {'pk8':153,'pk9':144,'pk10':504}
NSIM, L = 4000, 6

def sim(N,m,rec,r):
    off=int(r.integers(0,len(SRC)-N)); p=to_idx(col_enc(SRC[off:off+N],list(r.permutation(9))),KA).astype(np.int64)
    k=np.zeros(N,dtype=np.int64); k[:L]=r.integers(0,m,L)
    for i in range(L,N): k[i]=(k[i-L]+k[i-L+1])%m if rec=='aca' else (k[i-L]+k[i-1])%m
    return ioc(to_str((p+int(DS[r.integers(0,len(DS))])*k)%26,KA))

rows=[]
for tag,N in NS.items():
    print(f"\n{tag}  n={N}  observed IoC {OBS[tag]:.5f}")
    print(f"  {'m':>2s} {'rec':5s} {'mean':>8s} {'sd':>7s} {'z':>7s} {'P(sim>=obs)':>12s}  verdict")
    ok={'aca':[],'lag1':[]}
    for rec in ('aca','lag1'):
        for m in range(2,27):
            r=np.random.default_rng(abs(hash((tag,m,rec)))%(2**31))
            io=np.array([sim(N,m,rec,r) for _ in range(NSIM)])
            pg=float((io>=OBS[tag]).mean()); z=(OBS[tag]-io.mean())/io.std()
            cons = 0.025 <= pg <= 0.975
            if cons: ok[rec].append(m)
            rows.append({'target':tag,'m':m,'rec':rec,'mean':round(float(io.mean()),5),
                         'sd':round(float(io.std()),5),'z':round(float(z),2),'p_ge':pg,'consistent':cons})
            print(f"  {m:2d} {rec:5s} {io.mean():8.5f} {io.std():7.5f} {z:+7.2f} {pg:12.4f}  "
                  f"{'consistent' if cons else 'EXCLUDED'}",flush=True)
    for rec in ('aca','lag1'):
        v=ok[rec]
        print(f"  -> {tag} {rec}: consistent m = {v if v else 'NONE'}",flush=True)
json.dump({'obs':OBS,'rows':rows,'nsim':NSIM,'L':L},open('results/smallmod_minterval.json','w'),indent=1)
