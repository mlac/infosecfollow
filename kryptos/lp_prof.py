"""SCORER (a2): sorted-profile log-likelihood -- strictly more powerful than IoC, and
still fully invariant to (i) any transposition underneath and (ii) the unknown
monoalphabetic substitution in each residue class.

For a class with letter counts c and English letter probabilities q, the maximum over all
26! relabellings of sum_j c_j log q_{sigma(j)} is attained by sorting both descending
(rearrangement inequality). So S2(p) = (1/n) * sum_classes sum_j c_(j) log q_(j) is the
EXACT max-likelihood evidence a class-wise test can extract. IoC is a crude quadratic
proxy for it. Same matched null: 2000 letter-shuffles of the same ciphertext.

Also emits the information-theoretic power bound: a period-p polyalphabetic with an
unknown transposition underneath leaves NO usable structure except the within-class letter
profiles, so the pair count Npairs(p) = sum_r m_r(m_r-1)/2 is the entire evidence budget.
"""
import numpy as np, json, sys, time
sys.path.insert(0, '.')
from lib import CT, PT, AZ
from lp_ioc import idx, PERIODS

RNG = np.random.default_rng(4242)
NSHUF = 2000
ENG = idx(''.join(PT[k] for k in PT))
q = np.bincount(ENG, minlength=26).astype(float) + 1.0  # Laplace: PT corpus lacks some rare letters
q /= q.sum()
QS = np.log(np.sort(q)[::-1])          # sorted-descending English log-probs

def prof_score(M, p):
    """M: (N,n) -> (N,) mean-per-letter sorted-profile loglik."""
    N, n = M.shape
    tot = np.zeros(N)
    for r in range(p):
        cols = np.arange(r, n, p)
        if len(cols) < 2: continue
        sub = M[:, cols]
        off = (np.arange(N) * 26)[:, None]
        cnt = np.bincount((off + sub).ravel(), minlength=N*26).reshape(N, 26)
        cnt = -np.sort(-cnt, axis=1)                     # descending
        tot += cnt @ QS
    return tot / n

def npairs(n, p):
    return sum(m*(m-1)//2 for m in (len(range(r, n, p)) for r in range(p)))

if __name__ == '__main__':
    t0 = time.time(); out = {}
    for name in ['pk3', 'pk4', 'pk8', 'pk9', 'pk10']:
        C = idx(CT[name]); n = len(C)
        SH = np.array([RNG.permutation(C) for _ in range(NSHUF)])
        rows = []; ZS = np.zeros((NSHUF, len(PERIODS)))
        for j, p in enumerate(PERIODS):
            o = prof_score(C[None, :], p)[0]
            nl = prof_score(SH, p)
            mu, sd = nl.mean(), nl.std()
            ZS[:, j] = (nl - mu)/sd
            z = (o - mu)/sd
            # analytic z-ceiling from the pair budget (IoC-equivalent)
            Np = npairs(n, p)
            rows.append(dict(p=p, obs=float(o), null_mean=float(mu), null_sd=float(sd),
                             null_max=float(nl.max()), z=float(z),
                             p_emp=float((nl >= o).mean()), npairs=Np,
                             z_analytic_bound=round(0.1335*np.sqrt(Np), 2),
                             above_null_max=bool(o > nl.max())))
        mz = ZS.max(1); obsmax = max(r['z'] for r in rows)
        fam = dict(obs_maxz=float(obsmax), obs_argmax=int(max(rows, key=lambda r: r['z'])['p']),
                   null_maxz_mean=float(mz.mean()), null_maxz_p95=float(np.quantile(mz, .95)),
                   null_maxz_max=float(mz.max()), fam_p=float((mz >= obsmax).mean()), nshuf=NSHUF)
        out[name] = dict(rows=rows, family=fam)
        print(f"=== {name} n={n}  famMaxZ={obsmax:+.2f} @p={fam['obs_argmax']}  "
              f"nullMaxZ mean={mz.mean():.2f} p95={np.quantile(mz,.95):.2f} max={mz.max():.2f}  "
              f"FAMILYWISE p={fam['fam_p']:.4f}", flush=True)
        for r in sorted(rows, key=lambda r: -r['z'])[:3]:
            print(f"    p={r['p']:3d} z={r['z']:+6.2f} pairs={r['npairs']:5d} "
                  f"zbound={r['z_analytic_bound']:5.2f} p_emp={r['p_emp']:.4f}"
                  f"{'  ABOVE-NULLMAX' if r['above_null_max'] else ''}", flush=True)
    json.dump(out, open('results/lp_prof_raw.json','w'))
    print(f"wall {time.time()-t0:.1f}s")
