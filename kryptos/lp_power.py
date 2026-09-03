"""Power calibration for SCORER (a): synthetic positive controls at the REAL lengths.

For each n in {153 (pk8), 144 (pk9), 504 (pk10)} and each p in 25..72 we build NSYN
synthetic ciphertexts = period-p Vigenere over a random window of REAL English (the seven
solved plaintexts), optionally with a random full permutation applied first (to prove
transposition-invariance), then score exactly as the real search does, with a matched
per-instance shuffle null. Detection = z exceeds the family-wise ceiling T (95th pct of
the null max-over-48-periods z for that length).
"""
import numpy as np, json, time, sys
sys.path.insert(0, '.')
from lib import CT, PT, AZ
from lp_ioc import idx, stat_matrix, PERIODS

RNG = np.random.default_rng(7)
NSYN = 60
NNULL = 200
ENG = idx(''.join(PT[k] for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7']))

def famceiling(n, nshuf=2000):
    """family-wise null max-z ceiling for a text of length n with English-ish letter mix."""
    base = ENG[:n].copy()
    SH = np.array([RNG.permutation(base) for _ in range(nshuf)])
    ZS = np.zeros((nshuf, len(PERIODS)))
    for j, p in enumerate(PERIODS):
        nm, _, _ = stat_matrix(SH, p)
        mu, sd = nm.mean(), nm.std()
        ZS[:, j] = (nm - mu) / sd
    mz = ZS.max(1)
    return float(np.quantile(mz, 0.95)), float(mz.mean()), float(mz.max())

def synth(n, p, transpose):
    st = RNG.integers(0, len(ENG) - n)
    t = ENG[st:st+n].copy()
    if transpose:
        t = RNG.permutation(t)
    k = RNG.integers(0, 26, size=p)
    return (t + k[np.arange(n) % p]) % 26

def zscore(C, p, nnull=NNULL):
    obs, _, _ = stat_matrix(C[None, :], p)
    SH = np.array([RNG.permutation(C) for _ in range(nnull)])
    nm, _, _ = stat_matrix(SH, p)
    mu, sd = nm.mean(), nm.std()
    return float((obs[0] - mu) / sd) if sd > 0 else 0.0

if __name__ == '__main__':
    t0 = time.time(); out = {}
    for label, n in [('pk8', 153), ('pk9', 144), ('pk10', 504)]:
        T, mmean, mmax = famceiling(n)
        rows = []
        for p in PERIODS:
            for transpose in (False, True):
                zs = [zscore(synth(n, p, transpose), p) for _ in range(NSYN)]
                zs = np.array(zs)
                rows.append(dict(p=p, transposed=transpose, nsyn=NSYN,
                                 z_mean=float(zs.mean()), z_med=float(np.median(zs)),
                                 det_rate=float((zs > T).mean()),
                                 minclass=min(len(range(r, n, p)) for r in range(p))))
        out[label] = dict(n=n, ceiling95=T, null_maxz_mean=mmean, null_maxz_max=mmax, rows=rows)
        print(f"\n### {label} n={n}  ceiling T(95% famwise)={T:.2f} (null maxz mean {mmean:.2f}, max {mmax:.2f})", flush=True)
        for tr in (False, True):
            rs = [r for r in rows if r['transposed'] == tr]
            print(f"  transposed={tr}:", flush=True)
            for r in rs:
                if r['p'] % 4 == 1 or r['p'] in (25, 72):
                    print(f"    p={r['p']:3d} cls>={r['minclass']} zmed={r['z_med']:+5.2f} det={r['det_rate']:.2f}", flush=True)
            # first period where detection dies
            dead = [r['p'] for r in rs if r['det_rate'] < 0.20]
            print(f"    det<0.20 at p in {dead[:1] or ['none']} .. ; det>=0.80 up to p={max([r['p'] for r in rs if r['det_rate']>=0.80], default=None)}", flush=True)
        json.dump(out, open('results/lp_power_raw.json','w'))
    print(f"\nwall {time.time()-t0:.1f}s")
