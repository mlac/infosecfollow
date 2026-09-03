"""Transposition-invariant period exclusion with a POWER CURVE, saved to JSON.
Statistic: mean IoC of residue classes mod p. Null: identical statistic on letter-shuffled
copies of the SAME ciphertext. Power: identical statistic on synthetic period-p ciphertexts
built from real sibling-plaintext English put through a W8 columnar (so transposition-invariance
is exercised, not assumed)."""
import numpy as np, json, sys
from lib import *
rng = np.random.default_rng(31337)
ENG = ''.join(PT[k] for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7'])
def eng(n): i = rng.integers(0, len(ENG)-n); return ENG[i:i+n]
def stat(s, p): return float(np.mean([ioc(s[r::p]) for r in range(p) if len(s[r::p]) > 3]))

tag = sys.argv[1]; NSH = int(sys.argv[2]); NSIM = int(sys.argv[3])
ct = CT[tag]; n = len(ct)
ps = [p for p in range(2, 121) if n // p >= 5]
sh = [''.join(rng.permutation(list(ct))) for _ in range(NSH)]
out = []
for p in ps:
    nv = np.array([stat(s, p) for s in sh]); mu, sd = nv.mean(), nv.std()
    zo = (stat(ct, p) - mu) / sd
    zs = []
    for _ in range(NSIM):
        pt = eng(n); k = rng.integers(0, 26, p)
        c = to_str((to_idx(col_enc(pt, (6,2,3,5,1,4,0,7)))[:n] + k[np.arange(n) % p]) % 26)
        zs.append((stat(c, p) - mu) / sd)
    zs = np.array(zs)
    out.append({'p': p, 'obs_z': round(float(zo), 3), 'null_mu': round(float(mu), 5),
                'null_sd': round(float(sd), 5), 'true_z_mean': round(float(zs.mean()), 2),
                'true_z_sd': round(float(zs.std()), 2), 'power_at_z3': float((zs > 3).mean())})
    print(f"{tag} p={p:3d} obs z {zo:+6.2f}  true-cipher z {zs.mean():+6.2f}+-{zs.std():4.2f}  power {(zs>3).mean():.2f}", flush=True)
json.dump({'target': tag, 'n': n, 'nshuffle': NSH, 'nsim': NSIM, 'rows': out},
          open(f'results/period_{tag}.json', 'w'), indent=1)
excl = [r['p'] for r in out if r['power_at_z3'] >= 0.8 and r['obs_z'] < 2.5]
blind = [r['p'] for r in out if r['power_at_z3'] < 0.5]
print(f"\n{tag}: EXCLUDED periods (power>=.8, obs z<2.5): {excl}")
print(f"{tag}: test BLIND (power<.5): {blind}")
