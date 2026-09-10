"""Blind Hill row recovery, k x k, with an additive offset of period P.

For a decryption row r, the sequence s_b = r . c_b over blocks b equals p[k*b + j] + off[b mod P]
if r is a true row of the inverse matrix. So within each residue class mod P the sequence is a
SHIFTED copy of every k-th plaintext letter, and its IoC is English -- shift-invariant, so the
offset never has to be guessed. Score = mean over classes mod P of IoC.

The prior campaign's false lead was a DEGENERATE row: if gcd(r_1..r_k, 26) > 1 the map c -> r.c
cannot cover all 26 residues and the IoC is inflated for free. Those rows are excluded here, and
the matched null applies the identical exclusion.
"""
import numpy as np, itertools, json, sys
from math import gcd
from lib import KA, AZ, CT, PT, to_idx, to_str, ioc

def rows_for(k):
    R = np.array(list(itertools.product(range(26), repeat=k)), dtype=np.int64)
    g = np.gcd.reduce(np.concatenate([R, np.full((len(R),1), 26)], axis=1), axis=1)
    return R[g == 1]                      # exclude degenerate rows

def score_rows(C, k, P, R, chunk=20000):
    nb = len(C)//k
    B = C[:nb*k].reshape(nb, k)
    out = np.zeros(len(R))
    for s in range(0, len(R), chunk):
        Rc = R[s:s+chunk]
        S = (Rc @ B.T) % 26                       # (rows, nb)
        tot = np.zeros(len(Rc))
        for j in range(P):
            X = S[:, j::P]; L = X.shape[1]
            if L < 4: continue
            off = (np.arange(X.shape[0])*26)[:, None]
            cnt = np.bincount((off+X).ravel(), minlength=X.shape[0]*26).reshape(-1,26).astype(float)
            tot += (cnt*(cnt-1)).sum(1)/(L*(L-1))
        out[s:s+chunk] = tot/P
    return out

def run(tag, ks, Ps, alphas, nshuf, seed=17):
    rng = np.random.default_rng(seed); ct = CT[tag]; res = []
    for an, al in alphas:
        C = to_idx(ct, al).astype(np.int64)
        SH = [to_idx(''.join(rng.permutation(list(ct))), al).astype(np.int64) for _ in range(nshuf)]
        for k in ks:
            if len(ct) % k: continue
            R = rows_for(k)
            for P in Ps:
                o = score_rows(C, k, P, R)
                nm = []
                for X in SH: nm.append(float(score_rows(X, k, P, R).max()))
                res.append({'alpha': an, 'k': k, 'P': P, 'n_rows': int(len(R)),
                            'best': float(o.max()), 'best_row': R[int(o.argmax())].tolist(),
                            'mu': float(o.mean()), 'sd': float(o.std()),
                            'z': float((o.max()-o.mean())/o.std()),
                            'null_mean': float(np.mean(nm)), 'null_max': float(np.max(nm)),
                            'above': bool(o.max() > np.max(nm))})
                print(f"  {tag} {an} k={k} P={P}: rows={len(R)} best IoC {o.max():.4f} "
                      f"null mean {np.mean(nm):.4f} max {np.max(nm):.4f} "
                      f"{'<== ABOVE CEILING' if o.max()>np.max(nm) else ''}", flush=True)
    return res
