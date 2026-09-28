"""Deep autopsy of PK8 period 7 under the mutual-IoC statistic.
Doctrine: print the hit, print the decrypt, state the multiple-testing expectation, and check
whether the aligned distribution actually looks like a LANGUAGE and not merely a peaked one."""
import numpy as np
from lib import *
from mutual_ioc import hists, align
rng = np.random.default_rng(2024)
ENG = ''.join(PT[k] for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7'])
engfreq = np.array([ENG.count(c) for c in AZ], float); engfreq /= engfreq.sum()
engsorted = np.sort(engfreq)[::-1]

ct = CT['pk8']; n = len(ct); p = 7
C = to_idx(ct, KA).astype(int)[None, :]
obs, ks = align(hists(C, p), 60, rng)
print(f"PK8 p=7 mutual-IoC = {obs[0]:.5f}   shifts = {ks[0].tolist()}  key(KA) = {to_str(np.array(ks[0]))}")

# 2000-shuffle ceiling
SH = np.array([to_idx(''.join(rng.permutation(list(ct))), KA) for _ in range(2000)], dtype=int)
nv, _ = align(hists(SH, p), 30, rng)
print(f"  matched null over 2000 shuffles: mean {nv.mean():.5f} sd {nv.std():.5f} "
      f"max {nv.max():.5f} p99.9 {np.percentile(nv,99.9):.5f}")
print(f"  observed exceeds {(nv < obs[0]).mean()*100:.2f}% of nulls -> empirical p = {(nv>=obs[0]).mean():.4f}")

# what does the aligned text actually look like?
dec = to_str((to_idx(ct, KA).astype(int) - np.array(ks[0])[np.arange(n) % p]) % 26, KA)
H = np.bincount([KAI[c] for c in dec], minlength=26).astype(float); H /= H.sum()
print(f"\n  aligned residual (transposition may still scramble the ORDER, so read the STATS):")
print(f"    {dec}")
print(f"    IoC {ioc(dec):.4f}   English 0.0647, random 0.0385")
srt = np.sort(H)[::-1]
print(f"    sorted profile  obs: {' '.join(f'{v:.3f}' for v in srt[:8])}")
print(f"    sorted profile  eng: {' '.join(f'{v:.3f}' for v in engsorted[:8])}")
print(f"    chi2 sorted-profile vs English: {(((srt-engsorted)**2)/np.maximum(engsorted,1e-4)).sum()*n:.1f}")
nullsp = []
for _ in range(2000):
    s = ''.join(rng.permutation(list(ct)))
    Cx = to_idx(s, KA).astype(int)[None, :]
    o2, k2 = align(hists(Cx, p), 30, rng)
    d2 = (Cx[0] - np.array(k2[0])[np.arange(n) % p]) % 26
    h2 = np.bincount(d2, minlength=26).astype(float); h2 /= h2.sum()
    nullsp.append((((np.sort(h2)[::-1]-engsorted)**2)/np.maximum(engsorted,1e-4)).sum()*n)
print(f"    matched null for that chi2: mean {np.mean(nullsp):.1f} min {np.min(nullsp):.1f} "
      f"(LOWER is more English-like) -> observed is {'BETTER' if (((srt-engsorted)**2)/np.maximum(engsorted,1e-4)).sum()*n < np.min(nullsp) else 'NOT better'} than every null")
