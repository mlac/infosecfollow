"""ARCHITECTURAL GAP: every transposition-invariant result so far assumes transpose-then-substitute
(what PK4 and PK6 do). Test the other order: substitute-then-transpose.

If ct = col_enc(sub, perm) with width W and n divisible by W, then ciphertext block j (a contiguous
run of n/W letters, whose boundaries depend only on W and n, NOT on perm) is sub[perm[j]::W].
Its element t sits at substituted position perm[j] + tW, so if the substitution has period P the
key index inside a block advances by W each step and repeats with period q = P/gcd(W,P).
So: scan (W, q) and take the mean IoC of block_j[r::q] over all blocks and residues. This detects
the substitution WITHOUT knowing perm -- the unknown offset perm[j] only shifts which key letter a
block starts on, which IoC does not care about.
"""
import numpy as np, json, sys
from lib import *
rng = np.random.default_rng(6161)
ENG = ''.join(PT[k] for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7'])
def eng(n): i = rng.integers(0, len(ENG)-n); return ENG[i:i+n]

def stat(s, W, q):
    n = len(s); L = n // W
    vals = []
    for j in range(W):
        blk = s[j*L:(j+1)*L]
        for r in range(q):
            sub = blk[r::q]
            if len(sub) > 3: vals.append(ioc(sub))
    return float(np.mean(vals)) if vals else 0.0

def run(tag, NSH=300, NSIM=60):
    ct = CT[tag]; n = len(ct)
    Ws = [W for W in range(2, 25) if n % W == 0 and n//W >= 8]
    SH = [''.join(rng.permutation(list(ct))) for _ in range(NSH)]
    rows = []
    for W in Ws:
        for q in range(1, min(13, n//W//5) + 1):
            nv = np.array([stat(s, W, q) for s in SH]); mu, sd = nv.mean(), nv.std()
            zo = (stat(ct, W, q) - mu) / sd
            zs = []
            for _ in range(NSIM):
                P = q * W if q > 1 else W          # a period whose induced in-block period is q
                pt = eng(n); k = rng.integers(0, 26, P)
                sub = to_str((to_idx(pt) + k[np.arange(n) % P]) % 26)
                perm = list(rng.permutation(W))
                c = col_enc(sub, perm)
                zs.append((stat(c, W, q) - mu) / sd)
            zs = np.array(zs)
            rows.append({'W': W, 'q': q, 'obs_z': round(float(zo), 2),
                         'true_z_mean': round(float(zs.mean()), 2),
                         'power': float((zs > 3).mean())})
            print(f"  {tag} W={W:2d} q={q:2d}: obs z {zo:+6.2f}  true-cipher z {zs.mean():+6.2f}  "
                  f"power {(zs>3).mean():.2f}", flush=True)
    return rows

if __name__ == '__main__':
    out = {}
    for tag in sys.argv[1:]:
        print(f"--- {tag} (substitute-then-transpose) ---")
        out[tag] = run(tag)
    json.dump(out, open('results/outer_transpo.json', 'w'), indent=1)
    for tag, rows in out.items():
        mx = max(rows, key=lambda r: r['obs_z'])
        cov = [r for r in rows if r['power'] >= 0.8]
        print(f"\n{tag}: {len(rows)} (W,q) cells, max obs z {mx['obs_z']:+.2f} at W={mx['W']} q={mx['q']}; "
              f"{len(cov)}/{len(rows)} cells had power>=0.8")
