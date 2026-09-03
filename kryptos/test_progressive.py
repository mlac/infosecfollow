"""Positive control: can the scan recover a progressive key it built itself?"""
import numpy as np
from lib import *
from progressive import *
rng = np.random.default_rng(24)
ENG = ''.join(PT[k] for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7'])
for n in (504, 153, 144):
  for kind, p, d in (('block',7,1), ('block',9,3), ('letter',5,1), ('quad',6,1)):
    pt = ENG[:n]
    tr = col_enc(pt, (6,2,3,5,1,4,0,7))[:n]
    key = rng.integers(0,26,p)
    k = (key[np.arange(n)%p] + progression(kind,n,p,d)) % 26
    ct = to_str((to_idx(tr)+k)%26)
    rows = scan(ct, KA, [kind], range(2,13), range(0,6), nshuf=100, rng=np.random.default_rng(1))
    rows.sort(key=lambda r:-r['z']); top = rows[0]
    hit = [r for r in rows if r['p']==p and r['d']==d]
    print(f"n={n} true {kind} p={p} d={d} (eff period {p*26//np.gcd(d,26)}): "
          f"true cell z={hit[0]['z']:+.1f} rank {rows.index(hit[0])+1}/{len(rows)} | "
          f"top cell {top['kind']} p={top['p']} d={top['d']} z={top['z']:+.1f}")
