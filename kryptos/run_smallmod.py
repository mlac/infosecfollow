import numpy as np, json, time, sys
from smallmod import run_cell
from lib import KA, AZ, CT, to_idx
DS=[d for d in range(1,26) if np.gcd(d,26)==1]
CELLS=[(m,L) for m in (3,4,5,6,7,8) for L in range(3,10) if 10 <= m**L <= 1_000_000]
rng=np.random.default_rng(606)
out=[]; t0=time.time(); TOT=0
for tag in ('pk9','pk8','pk10'):
    ct=CT[tag]; n=len(ct)
    SH=[''.join(rng.permutation(list(ct))) for _ in range(4)]
    for an,al in (('KA',KA),('AZ',AZ)):
        C=to_idx(ct,al).astype(np.int64)
        CS=[to_idx(s,al).astype(np.int64) for s in SH]
        for m,L in CELLS:
            for rec in ('aca','lag1'):
                (io,d,p),nc=run_cell(C,m,L,rec,DS,n); TOT+=nc
                nulls=[]
                for Cx in CS:
                    (io2,_,_),nc2=run_cell(Cx,m,L,rec,DS,n); nulls.append(io2); TOT+=nc2
                out.append({'target':tag,'alpha':an,'m':m,'L':L,'rec':rec,'obs':round(io,5),
                            'd':d,'primer':list(p),'null_mean':round(float(np.mean(nulls)),5),
                            'null_max':round(float(np.max(nulls)),5),
                            'above':bool(io>np.max(nulls))})
        print(f"  {tag} {an}: {len(out)} cells, {TOT:,} configs, {time.time()-t0:.0f}s",flush=True)
json.dump({'cells':out,'n_configs':TOT,'wall':round(time.time()-t0,1)},open('results/smallmod.json','w'),indent=1)
ab=[c for c in out if c['above']]
print(f"\n=== SMALL-MODULUS LAGGED-FIBONACCI KEYSTREAMS ===")
print(f"  {len(out)} cells, {TOT:,} configurations, {time.time()-t0:.0f}s")
print(f"  cells above their matched null max: {len(ab)}")
for c in sorted(out,key=lambda c:-(c['obs']-c['null_max']))[:8]:
    print(f"   {c['target']} {c['alpha']} m={c['m']} L={c['L']} {c['rec']}: obs {c['obs']:.4f} "
          f"nullmax {c['null_max']:.4f} delta {c['obs']-c['null_max']:+.4f}")
