"""Power test for the UNBALANCED enumeration -- decides whether its PK9 negative is Tier 2 or 3.

partition_unbal.py returned obs -456.80 (KA) and -465.22 (AZ) against null maxima of -452.56 and
-457.64: below ceiling in both alphabets.  That is only informative if a genuine unbalanced key
would have cleared those same ceilings.  So plant unbalanced keys at n=144 and score the FULL
64,570,082-partition enumeration, exactly as the real run did.
"""
import numpy as np, json, time
from lib import KA, PT, to_idx, col_enc
from partition_power import prep
from partition_llr import score_llr
from partition_unbal import gen_canonical

P, J, N = 18, 3, 144
CEIL = {'KA': -452.56, 'AZ': -457.64}      # measured null maxima from the real run
SRC = ''.join(PT[k] for k in ('pk2','pk3','pk5','pk6','pk7','pk4','pk1'))

def plant_unbalanced(seed, W=9):
    r = np.random.default_rng(seed)
    while True:                                     # insist on a genuinely lopsided key
        a = r.integers(0, J, P)
        c = np.bincount(a, minlength=J)
        if c.min() >= 2 and c.max() - c.min() >= 3: break
    S = r.permutation(26)[:J]
    off = int(r.integers(0, len(SRC)-N))
    x = to_idx(col_enc(SRC[off:off+N], list(r.permutation(W))), KA).astype(np.int64)
    return (x + np.resize(S[a], N)) % 26, a, c

t0 = time.time(); res = []
print(f"planted UNBALANCED keys at n={N}, p={P}, j={J}; full {64_570_082:,}-partition enumeration")
print(f"real-run ceilings to beat: KA {CEIL['KA']:.2f}, AZ {CEIL['AZ']:.2f}\n", flush=True)
for rep in range(4):
    C, a, sizes = plant_unbalanced(6000 + rep*17)
    cnt, _ = prep(C, P)
    best, bestA, ncfg = -1e18, None, 0
    for A in gen_canonical(P, J):
        s = score_llr(A.astype(np.int64), cnt, J); ncfg += len(A)
        i = int(s.argmax())
        if s[i] > best: best, bestA = float(s[i]), A[i].copy()
    truth = float(score_llr(a[None, :], cnt, J)[0])
    exact = np.array_equal(np.asarray(bestA), a)
    res.append({'rep':rep,'sizes':sizes.tolist(),'best':round(best,2),'truth':round(truth,2),
                'exact':bool(exact),'beats_KA':best > CEIL['KA'],'beats_AZ':best > CEIL['AZ'],
                'n_partitions':ncfg})
    print(f"  plant {rep} sizes {sizes.tolist()}: best {best:9.2f}  truth {truth:9.2f}  "
          f"exact {str(exact):5s}  beats KA ceiling {best > CEIL['KA']}  "
          f"AZ {best > CEIL['AZ']}  ({time.time()-t0:.0f}s)", flush=True)
    json.dump({'reps':res,'ceilings':CEIL,'wall':round(time.time()-t0,1)},
              open('results/partition_unbal_power.json','w'), indent=1)
nk = sum(r['beats_KA'] for r in res); ne = sum(r['exact'] for r in res)
print(f"\n=== {nk}/{len(res)} planted unbalanced keys clear the real KA ceiling; "
      f"{ne}/{len(res)} recovered exactly.  {time.time()-t0:.0f}s ===", flush=True)
