"""Feasibility probe: can a constrained-partition search see item 0a's surviving shape?

The shape: key of period p built from only j distinct letters.  Then the p residue classes mod p are
monoalphabetic, and classes sharing a key value merge into ONE monoalphabetic group of n/j letters.
n/j is large enough to see English even when n/p is not -- which is the whole point, since §F15's
information bound bites on the p classes individually, not on the j groups.

Unlike §G2's Tier 1 impossibility (partitioning POSITIONS freely, a pure census function with zero
power), partitioning RESIDUE CLASSES is constrained: classes must stay whole.  That constraint is
what could carry signal.  This probe asks whether it actually does, before any search is built.

Cheap question first: does the TRUE partition outscore random partitions of the same shape?
If it does not, no amount of enumeration helps and the shape is unreachable -- worth knowing.
"""
import numpy as np
from lib import KA, PT, to_idx, to_str, ioc, col_enc
SRC = ''.join(PT[k] for k in ('pk2','pk3','pk5','pk6','pk7','pk4','pk1'))

def plant(N, p, j, seed, W=9):
    r = np.random.default_rng(seed)
    off = int(r.integers(0, len(SRC)-N))
    pt = col_enc(SRC[off:off+N], list(r.permutation(W))) if W else SRC[off:off+N]
    x = to_idx(pt, KA).astype(np.int64)
    S = r.permutation(26)[:j]
    assign = r.integers(0, j, p)              # which of the j letters each class uses
    key = S[assign]
    c = (x + np.resize(key, N)) % 26
    return c, assign

def score(c, p, assign, j):
    """mean IoC over the j merged groups"""
    tot, nb = 0.0, 0
    for b in range(j):
        cls = [i for i in range(p) if assign[i] == b]
        if not cls: continue                      # empty block -> that group simply does not exist
        idx = np.concatenate([np.arange(i, len(c), p) for i in cls])
        if len(idx) < 2: continue
        cnt = np.bincount(c[idx] % 26, minlength=26).astype(float)
        tot += (cnt*(cnt-1)).sum()/(len(idx)*(len(idx)-1)); nb += 1
    return tot/nb if nb else -1

print(f"{'n':>4s} {'p':>3s} {'j':>2s} {'true':>8s} {'rand mean':>10s} {'rand max':>9s} "
      f"{'z':>7s} {'rank of true':>13s}")
for N in (144, 504):
    for p in (18, 24, 36):
        for j in (3, 4, 5):
            zs, ranks = [], []
            for rep in range(12):
                c, a = plant(N, p, j, 700 + 100*rep + p + j)
                t = score(c, p, a, j)
                r = np.random.default_rng(5000 + rep)
                rnd = np.array([score(c, p, r.integers(0, j, p), j) for _ in range(3000)])
                zs.append((t - rnd.mean())/rnd.std())
                ranks.append(int((rnd >= t).sum()))
            print(f"{N:4d} {p:3d} {j:2d} {t:8.5f} {rnd.mean():10.5f} {rnd.max():9.5f} "
                  f"{np.mean(zs):+7.2f} {np.mean(ranks):10.1f}/3000", flush=True)
