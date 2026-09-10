"""Power test for the small-modulus lagged-Fibonacci sweep (run_smallmod.py).

Doctrine (user brief, and my own §A0): a negative from a ranking search is worthless unless the
identical search, run on text that genuinely contains the target, clears the SAME family-wise
ceiling.  §A0 already showed that at 144-153 letters a true two-word product key scores BELOW the
noise floor of the grid hunting it.  This asks the same question of the small-modulus family.

Design
------
  plant   : real setter English (the seven solved plaintexts, concatenated and offset) encrypted
            with a genuine keystream  k[i] = (k[i-L] + k[i-L+1]) % m,  s[i] = d*k[i] mod 26,
            optionally with a W-column columnar applied to the PLAINTEXT first (PK4/PK6 order).
  search  : the identical grid run_smallmod.py runs -- every (m,L,rec) cell, argmax IoC over all
            m^L primers and all 12 multipliers.
  ceiling : the family-wise null max, i.e. the largest cell-best IoC over 4 letter-shuffles of the
            SAME planted ciphertext across ALL cells.  That is the number a real hit must beat.
  power   : repeat the true cell alone on fresh plants to get the distribution of the true obs.

A pass needs the true cell to (a) rank first and (b) beat the family-wise ceiling.  Anything less
means the sweep's silence carries no information at that length, and its verdict is Tier 3.
"""
import numpy as np, json, time, sys
from smallmod import run_cell
from lib import KA, AZ, PT, to_idx, to_str, ioc, col_enc

N      = int(sys.argv[1])          # target length: 144 (pk9), 153 (pk8) or 504 (pk10)
PLANT_M, PLANT_L, PLANT_REC = 5, 6, 'aca'
COLUMNAR_W = 9                     # transposition underneath, as in PK4/PK6
NPLANT = 5                         # plant realisations for the true-cell distribution
DS   = [d for d in range(1, 26) if np.gcd(d, 26) == 1]
CELLS = [(m, L) for m in (3,4,5,6,7,8) for L in range(3,10) if 10 <= m**L <= 1_000_000]

rng = np.random.default_rng(9091)
SRC = ''.join(PT[k] for k in ('pk2','pk3','pk5','pk6','pk7','pk4','pk1'))


def plant(seed):
    """genuine small-modulus ciphertext of length N over the KRYPTOS alphabet"""
    r = np.random.default_rng(seed)
    off = int(r.integers(0, len(SRC) - N))
    pt = SRC[off:off+N]
    perm = list(r.permutation(COLUMNAR_W))
    pt = col_enc(pt, perm)                       # transposition innermost
    p = to_idx(pt, KA).astype(np.int64)
    k = np.zeros(N, dtype=np.int64)
    k[:PLANT_L] = r.integers(0, PLANT_M, PLANT_L)
    for i in range(PLANT_L, N):
        k[i] = (k[i-PLANT_L] + k[i-PLANT_L+1]) % PLANT_M
    d = int(DS[r.integers(0, len(DS))])
    return (p + d*k) % 26, d, tuple(k[:PLANT_L].tolist()), perm


t0 = time.time()
C, d_true, primer_true, perm_true = plant(1000)
print(f"# n={N}  plant m={PLANT_M} L={PLANT_L} {PLANT_REC} d={d_true} primer={primer_true} "
      f"columnar W={COLUMNAR_W} perm={perm_true}", flush=True)
print(f"# planted ciphertext IoC {ioc(to_str(C, KA)):.5f}   "
      f"(pk8 0.03947, pk9 0.04448, pk10 0.03877)", flush=True)

SH = [''.join(rng.permutation(list(to_str(C, KA)))) for _ in range(4)]
CS = [to_idx(s, KA).astype(np.int64) for s in SH]

cells, tot = [], 0
for m, L in CELLS:
    for rec in ('aca', 'lag1'):
        (io, d, p), nc = run_cell(C, m, L, rec, DS, N); tot += nc
        nulls = []
        for Cx in CS:
            (io2, _, _), nc2 = run_cell(Cx, m, L, rec, DS, N); nulls.append(io2); tot += nc2
        cells.append({'m': m, 'L': L, 'rec': rec, 'obs': round(io, 5), 'd': d,
                      'primer': list(p), 'null_max': round(float(np.max(nulls)), 5),
                      'null_mean': round(float(np.mean(nulls)), 5)})
        print(f"  m={m} L={L} {rec:5s} obs {io:.5f}  nullmax {np.max(nulls):.5f}  "
              f"{'TRUE CELL' if (m,L,rec)==(PLANT_M,PLANT_L,PLANT_REC) else ''}", flush=True)

fw = max(c['null_max'] for c in cells)
true = [c for c in cells if (c['m'], c['L'], c['rec']) == (PLANT_M, PLANT_L, PLANT_REC)][0]
rank = 1 + sum(1 for c in cells if c['obs'] > true['obs'])
best = max(cells, key=lambda c: c['obs'])

print(f"\n# family-wise null ceiling (max over {len(cells)} cells x 4 shuffles): {fw:.5f}", flush=True)
print(f"# true cell obs {true['obs']:.5f}  rank {rank}/{len(cells)}  "
      f"beats ceiling: {true['obs'] > fw}", flush=True)
print(f"# grid winner  m={best['m']} L={best['L']} {best['rec']} obs {best['obs']:.5f}", flush=True)
print(f"# primer recovered exactly: {tuple(true['primer']) == primer_true}  "
      f"(true {primer_true}, found {tuple(true['primer'])})", flush=True)

reps = []
for j in range(NPLANT):
    Cj, dj, pj, _ = plant(2000 + j)
    (io, d, p), nc = run_cell(Cj, PLANT_M, PLANT_L, PLANT_REC, DS, N); tot += nc
    reps.append({'obs': round(io, 5), 'primer_ok': tuple(p) == pj, 'd_ok': d == dj})
    print(f"  plant {j}: true-cell obs {io:.5f}  beats ceiling {io > fw}  "
          f"primer {'OK' if tuple(p)==pj else 'MISS'}", flush=True)

npass = sum(1 for r in reps if r['obs'] > fw)
json.dump({'n': N, 'plant': {'m': PLANT_M, 'L': PLANT_L, 'rec': PLANT_REC, 'W': COLUMNAR_W},
           'cells': cells, 'family_ceiling': fw, 'true_obs': true['obs'], 'true_rank': rank,
           'grid_winner': {'m': best['m'], 'L': best['L'], 'rec': best['rec'], 'obs': best['obs']},
           'primer_exact': tuple(true['primer']) == primer_true,
           'replications': reps, 'power': npass / len(reps),
           'n_configs': tot, 'wall': round(time.time()-t0, 1)},
          open(f'results/power_smallmod_{N}.json', 'w'), indent=1)
print(f"\n=== POWER n={N}: {npass}/{len(reps)} plants beat the family ceiling {fw:.5f}; "
      f"{tot:,} configs, {time.time()-t0:.0f}s ===", flush=True)
