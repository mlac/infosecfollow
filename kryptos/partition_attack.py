"""Run the exhaustive balanced-partition likelihood attack on the REAL targets.

Gated on partition_enum.py showing the attack has power at the target's length -- a negative from a
solver that cannot find a planted key is worth nothing, per the standing doctrine.

Hypothesis: the key has period p and uses j distinct letters, so the p residue classes merge into j
monoalphabetic groups.  Enumerate every balanced partition, score each by the best-shift English
log-likelihood of its merged groups, and compare the maximum against a null built by running the
IDENTICAL enumeration on letter-shuffles of the same ciphertext.  Shuffling preserves the census and
destroys the key structure, so the null is matched to the search by construction.

Cells are the ones whose balanced space is actually enumerable:
    p=18, j=2  ->     24,310      p=18, j=3 -> 2,858,856      p=24, j=2 -> 1,352,078
"""
import numpy as np, json, time, sys
from lib import KA, AZ, CT, to_idx, to_str
from partition_power import prep
from partition_llr import score_llr
from partition_enum import enum_balanced

CELLS  = [(18, 2), (18, 3), (24, 2)]
NNULL  = 30
rng    = np.random.default_rng(4242)
TARGETS = sys.argv[1:] or ['pk9', 'pk8', 'pk10']

ENUM = {}
for p, j in CELLS:
    t = time.time(); ENUM[(p, j)] = enum_balanced(p, j)
    print(f"enumerated p={p} j={j}: {len(ENUM[(p,j)]):,} partitions ({time.time()-t:.1f}s)", flush=True)

out = []; t0 = time.time(); tot = 0
for tag in TARGETS:
    ct = CT[tag]; n = len(ct)
    shuf = [''.join(rng.permutation(list(ct))) for _ in range(NNULL)]
    for an, al in (('KA', KA), ('AZ', AZ)):
        C  = to_idx(ct, al).astype(np.int64)
        CS = [to_idx(s, al).astype(np.int64) for s in shuf]
        for p, j in CELLS:
            A = ENUM[(p, j)]
            cnt, _ = prep(C, p)
            s = score_llr(A, cnt, j); obs = float(s.max()); best = A[int(s.argmax())]
            tot += len(A)
            nulls = []
            for Cx in CS:
                cx, _ = prep(Cx, p)
                nulls.append(float(score_llr(A, cx, j).max())); tot += len(A)
            nm, nsd, nmx = float(np.mean(nulls)), float(np.std(nulls)), float(np.max(nulls))
            z = (obs - nm)/nsd if nsd else 0.0
            above = obs > nmx
            out.append({'target': tag, 'alpha': an, 'p': p, 'j': j, 'obs': round(obs, 3),
                        'null_mean': round(nm, 3), 'null_sd': round(nsd, 3),
                        'null_max': round(nmx, 3), 'z': round(z, 2), 'above': above,
                        'partition': best.tolist()})
            print(f"  {tag} {an} p={p} j={j}: obs {obs:10.2f}  null {nm:10.2f} +- {nsd:5.2f}  "
                  f"max {nmx:10.2f}  z {z:+6.2f}  {'*** ABOVE CEILING ***' if above else ''}",
                  flush=True)
            json.dump({'cells': out, 'n_scorings': tot, 'nnull': NNULL,
                       'wall': round(time.time()-t0, 1)},
                      open('results/partition_attack.json', 'w'), indent=1)

ab = [c for c in out if c['above']]
print(f"\n=== {len(out)} cells, {tot:,} partition scorings, {time.time()-t0:.0f}s ===", flush=True)
print(f"  cells above their matched null max: {len(ab)}", flush=True)
for c in sorted(out, key=lambda c: -c['z'])[:6]:
    print(f"   {c['target']} {c['alpha']} p={c['p']} j={c['j']}: z {c['z']:+.2f}", flush=True)
