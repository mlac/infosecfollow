import numpy as np, itertools, json, sys, time
from lib import KA, AZ, CT
from crib_sweep import build_cribs, make_checker, derive_mat

CRIBS = build_cribs()
STRUCTS  = [(p,) for p in range(2, 25)]
STRUCTS += [(a, b) for a in range(3, 17) for b in range(a+1, 17)]
STRUCTS += [t for t in itertools.combinations(range(3, 15), 3)]
STRUCTS += [t for t in itertools.combinations(range(3, 11), 4)]
MAXFP = 1e-6
t0 = time.time(); hits = []; ntest = 0; efp = 0.0; nskip = 0
CK = {}
for tag in ('pk8', 'pk9', 'pk10'):
    n = len(CT[tag])
    for aname, alpha in (('KA', KA), ('AZ', AZ)):
        for mode in ('sub', 'add', 'beau'):
            for at_end in (False, True):
                D = derive_mat(CT[tag], CRIBS, alpha, mode, at_end)
                for m, (subs, pos, K) in D.items():
                    for st in STRUCTS:
                        key = (tuple(pos), st)
                        if key not in CK: CK[key] = make_checker(pos, st)
                        R2, R13, r2, r13 = CK[key]
                        fp = (2.0**-r2) * (13.0**-r13)
                        if fp > MAXFP: nskip += 1; continue
                        ok = np.ones(len(subs), bool)
                        if r2:  ok &= ((K @ R2.T) % 2 == 0).all(1)
                        if r13: ok &= ((K @ R13.T) % 13 == 0).all(1)
                        ntest += len(subs); efp += fp * len(subs)
                        for i in np.nonzero(ok)[0]:
                            hits.append({'target': tag, 'alpha': aname, 'mode': mode,
                                         'at_end': at_end, 'crib': subs[i], 'structure': list(st),
                                         'fp_rate': fp})
            print(f"  {tag} {aname} {mode}: cum tests {ntest:,} hits {len(hits)} "
                  f"({time.time()-t0:.0f}s)", flush=True)
json.dump({'n_cribs': len(CRIBS), 'n_structures': len(STRUCTS), 'n_tests': ntest,
           'expected_false_positives': efp, 'skipped_underpowered': nskip,
           'hits': hits, 'wall_sec': round(time.time()-t0, 1)},
          open('results/crib.json', 'w'), indent=1)
print(f"\n=== CRIB SWEEP: {len(CRIBS):,} cribs x {len(STRUCTS)} key structures x 3 targets"
      f" x 2 alphabets x 3 modes x {{prefix,suffix}} ===")
print(f"  effective tests executed : {ntest:,}   (underpowered structure/length combos skipped: {nskip:,})")
print(f"  EXPECTED false positives under the null : {efp:.2e}")
print(f"  OBSERVED passes : {len(hits)}")
for h in hits[:40]: print("   HIT", h)
