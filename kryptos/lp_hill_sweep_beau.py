"""SCORER (b) full sweep: periods 25-72 x {pk8,pk9,pk10} x {KA,AZ} text alphabet,
plus pk3 (KA) as the real positive control that the sweep must rank at p=40.

Matched null: NNULL fixed letter-shuffled copies per (text,alphabet), each run through
the IDENTICAL hill climb at every period with the IDENTICAL restart budget. Because the
shuffle bank is fixed across periods, each shuffle yields a max-over-periods z
trajectory -> a real family-wise ceiling, not just a per-period one.
"""
import numpy as np, sys, time, json
sys.path.insert(0, '.')
from lib import CT, KA, AZ
from lp_hill import climb, cidx, PERM, decrypt
SIGN = int(sys.argv[3]) if len(sys.argv) > 3 else 1
TAG = 'sub' if SIGN == 1 else 'beau'

R = int(sys.argv[1]) if len(sys.argv) > 1 else 40
NNULL = int(sys.argv[2]) if len(sys.argv) > 2 else 12
PERIODS = list(range(25, 73))
JOBS = ([('pk3', 'KA'), ('pk8', 'KA'), ('pk8', 'AZ'), ('pk9', 'KA'), ('pk9', 'AZ'),
         ('pk10', 'KA'), ('pk10', 'AZ')] if SIGN == 1 else
        [('pk3', 'KA'), ('pk8', 'KA'), ('pk8', 'AZ'), ('pk9', 'KA'), ('pk9', 'AZ')])

rng = np.random.default_rng(101)
out = {}; t0 = time.time(); nrun = 0
for name, alpha in JOBS:
    C = cidx(CT[name], alpha)
    bank = [rng.permutation(C) for _ in range(NNULL)]
    rows = []
    NZ = np.zeros((NNULL, len(PERIODS)))
    for j, P in enumerate(PERIODS):
        obs, K = climb(C, P, PERM[alpha], rng, R, sign=SIGN); nrun += 1
        nl = np.array([climb(b, P, PERM[alpha], rng, R, sign=SIGN)[0] for b in bank]); nrun += NNULL
        mu, sd = nl.mean(), nl.std()
        # leave-one-out z for each null so the family-wise ceiling is unbiased
        for i in range(NNULL):
            o = np.delete(nl, i)
            NZ[i, j] = (nl[i] - o.mean()) / (o.std() + 1e-12)
        z = (obs - mu) / (sd + 1e-12)
        rows.append(dict(p=P, obs=float(obs), null_mean=float(mu), null_sd=float(sd),
                         null_max=float(nl.max()), z=float(z),
                         above_null_max=bool(obs > nl.max()),
                         key=[int(v) for v in K],
                         pt=decrypt(C, K, KA if alpha == 'KA' else AZ, sign=SIGN)))
        print(f"  {name}/{alpha}/{TAG} p={P:3d} obs={obs:.4f} null={mu:.4f}+-{sd:.4f} "
              f"max={nl.max():.4f} z={z:+6.2f}{'  ABOVE-NULLMAX' if obs > nl.max() else ''} "
              f"[{time.time()-t0:.0f}s {nrun} runs]", flush=True)
    mz = NZ.max(1); obsmax = max(r['z'] for r in rows)
    fam = dict(obs_maxz=obsmax, obs_argmax=int(max(rows, key=lambda r: r['z'])['p']),
               null_maxz_mean=float(mz.mean()), null_maxz_max=float(mz.max()),
               fam_p=float((mz >= obsmax).mean()), nnull=NNULL, restarts=R)
    out[f"{name}_{alpha}_{TAG}"] = dict(rows=rows, family=fam)
    print(f"### {name}/{alpha}/{TAG} FAM obs_maxz={obsmax:+.2f} @p={fam['obs_argmax']} "
          f"nullmaxz mean={mz.mean():.2f} max={mz.max():.2f} fam_p={fam['fam_p']:.3f}", flush=True)
    json.dump(out, open(f'results/lp_hill_raw_{TAG}.json', 'w'))
print(f"DONE wall={time.time()-t0:.0f}s runs={nrun} configs={len(JOBS)*len(PERIODS)}")
