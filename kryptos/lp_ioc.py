"""FAMILY: long periods 25-72. SCORER (a): transposition-invariant residue-class IoC.

Statistic S(p) = mean over r=0..p-1 of IoC(C[r::p])  (classes with >=2 letters).

Why this covers the whole family: if C = E(T) where T is ANY permutation of the plaintext
(unknown columnar underneath) and E applies a fixed monoalphabetic substitution per position
mod p -- Vigenere / Beaufort / variant / Quagmire I-IV / arbitrary keyed alphabets, any
mixed alphabet -- then each class C[r::p] is a monoalphabetic image of a random sample of
English letters, so its IoC ~ English (.0647) instead of flat (.0385).

NOTE (stated, not hidden): S(p) counts coincidences of raw letters. Relabelling the alphabet
(KA <-> A-Z) is a bijection on letters and leaves every coincidence count unchanged, so
S(p) is IDENTICAL for the KA and A-Z text alphabets. There is no 2x here to claim.

Matched null: the identical statistic computed on letter-shuffled copies of the SAME
ciphertext (same length, same letter multiset), NSHUF per text, all 48 periods.
Ceiling = per-period max over shuffles AND the family-wise max-over-all-periods null.
"""
import numpy as np, json, time, sys
sys.path.insert(0, '.')
from lib import CT, AZ

RNG = np.random.default_rng(20260903)
PERIODS = list(range(25, 73))
NSHUF = 2000

def idx(s):
    a = {c: i for i, c in enumerate(AZ)}
    return np.array([a[c] for c in s], dtype=np.int64)

def ioc_rows_fast(R):
    """R: (N,L) ints 0..25 -> (N,) IoC"""
    N, L = R.shape
    if L < 2:
        return np.zeros(N)
    off = (np.arange(N, dtype=np.int64) * 26)[:, None]
    cnt = np.bincount((off + R).ravel(), minlength=N * 26).reshape(N, 26).astype(np.float64)
    return (cnt * (cnt - 1)).sum(1) / (L * (L - 1))

def stat_matrix(M, p):
    """M: (N,n) many texts. Returns (N,) mean class-IoC mod p, and (pooled_rate,) too."""
    N, n = M.shape
    tot = np.zeros(N); k = 0
    num = np.zeros(N); den = 0.0
    for r in range(p):
        cols = np.arange(r, n, p)
        m = len(cols)
        if m < 2:
            continue
        sub = M[:, cols]
        v = ioc_rows_fast(sub)
        tot += v; k += 1
        num += v * (m * (m - 1)); den += m * (m - 1)
    return tot / k, num / den, k

def classsizes(n, p):
    return [len(range(r, n, p)) for r in range(p)]

def run(name, ct, nshuf=NSHUF):
    C = idx(ct); n = len(C)
    SH = np.array([RNG.permutation(C) for _ in range(nshuf)])
    rows = []
    for p in PERIODS:
        obs_mean, obs_pool, k = stat_matrix(C[None, :], p)
        nul_mean, nul_pool, _ = stat_matrix(SH, p)
        mu, sd = nul_mean.mean(), nul_mean.std()
        z = (obs_mean[0] - mu) / sd if sd > 0 else 0.0
        cs = classsizes(n, p)
        rows.append(dict(p=p, n=n, minclass=min(cs), maxclass=max(cs), nclass_used=k,
                         obs_mean=float(obs_mean[0]), obs_pool=float(obs_pool[0]),
                         null_mean=float(mu), null_sd=float(sd),
                         null_max=float(nul_mean.max()),
                         null_p999=float(np.quantile(nul_mean, 0.999)),
                         z=float(z), above_null_max=bool(obs_mean[0] > nul_mean.max()),
                         p_emp=float((nul_mean >= obs_mean[0]).mean())))
    # family-wise ceiling: distribution of max-z across all periods for each shuffle,
    # z-scored against the null of the OTHER shuffles (leave-one-out is overkill; use
    # per-period null mu/sd from the same shuffle bank).
    ZS = np.zeros((nshuf, len(PERIODS)))
    for j, p in enumerate(PERIODS):
        nm, _, _ = stat_matrix(SH, p)
        mu, sd = nm.mean(), nm.std()
        ZS[:, j] = (nm - mu) / sd
    fam = dict(obs_maxz=float(max(r['z'] for r in rows)),
               obs_argmax=int(max(rows, key=lambda r: r['z'])['p']),
               null_maxz_mean=float(ZS.max(1).mean()),
               null_maxz_max=float(ZS.max(1).max()),
               null_maxz_p95=float(np.quantile(ZS.max(1), 0.95)),
               null_maxz_p999=float(np.quantile(ZS.max(1), 0.999)),
               fam_p=float((ZS.max(1) >= max(r['z'] for r in rows)).mean()),
               nshuf=nshuf)
    return rows, fam

if __name__ == '__main__':
    t0 = time.time()
    out = {}
    targets = ['pk3', 'pk4', 'pk8', 'pk9', 'pk10']
    for name in targets:
        rows, fam = run(name, CT[name])
        out[name] = dict(rows=rows, family=fam)
        top = sorted(rows, key=lambda r: -r['z'])[:5]
        print(f"\n=== {name}  n={len(CT[name])}  famMaxZ={fam['obs_maxz']:.2f} @p={fam['obs_argmax']}"
              f"  nullMaxZ mean={fam['null_maxz_mean']:.2f} p95={fam['null_maxz_p95']:.2f} max={fam['null_maxz_max']:.2f}"
              f"  FAMILYWISE p={fam['fam_p']:.4f}", flush=True)
        for r in top:
            print(f"   p={r['p']:3d} cls={r['minclass']}-{r['maxclass']} obs={r['obs_mean']:.4f} "
                  f"null mu={r['null_mean']:.4f} sd={r['null_sd']:.4f} max={r['null_max']:.4f} "
                  f"z={r['z']:+.2f} {'ABOVE-NULLMAX' if r['above_null_max'] else ''}", flush=True)
    out['_meta'] = dict(periods=[PERIODS[0], PERIODS[-1]], nshuf=NSHUF,
                        wall_sec=round(time.time()-t0, 1),
                        configs=len(targets)*len(PERIODS))
    json.dump(out, open('results/lp_ioc_raw.json', 'w'))
    print(f"\nwall {time.time()-t0:.1f}s  configs={len(targets)*len(PERIODS)}")
