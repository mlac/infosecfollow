"""Synthetic positive control / power curve for SCORER (b) at the REAL lengths."""
import numpy as np, sys, time, json
sys.path.insert(0, '.')
from lib import PT, AZ, AZI
from lp_hill import climb, qrows, PERM

rng = np.random.default_rng(3)
ENG = np.array([AZI[c] for c in ''.join(PT[k] for k in PT)], dtype=np.int64)

def run(n, P, R, nsyn, nnull):
    hits = 0; zs = []
    for _ in range(nsyn):
        st = rng.integers(0, len(ENG)-n)
        t = ENG[st:st+n]
        k = rng.integers(0, 26, size=P)
        C = (t + k[np.arange(n) % P]) % 26
        s, K = climb(C, P, PERM['AZ'], rng, R)
        nn = np.array([climb(rng.permutation(C), P, PERM['AZ'], rng, R)[0] for _ in range(nnull)])
        z = (s - nn.mean())/(nn.std()+1e-9)
        zs.append(z)
        D = ''.join(AZ[int(v)] for v in (C - K[np.arange(n) % P]) % 26)
        tr = ''.join(AZ[int(v)] for v in t)
        acc = sum(a == b for a, b in zip(D, tr))/n
        hits += (acc > 0.9)
    return np.array(zs), hits/nsyn

if __name__ == '__main__':
    R = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    t0 = time.time(); out = {}
    for n in (153, 144, 504):
        for P in (25, 35, 45, 60, 72):
            zs, rec = run(n, P, R, 8, 6)
            out[f"{n}_{P}"] = dict(z_med=float(np.median(zs)), z_max=float(zs.max()), recov=rec)
            print(f"n={n} P={P} R={R}: z med={np.median(zs):+6.2f} max={zs.max():+6.2f} "
                  f"exact-recovery(>90% letters)={rec:.2f}  [{time.time()-t0:.0f}s]", flush=True)
    json.dump(out, open('results/lp_hill_power.json','w'))
