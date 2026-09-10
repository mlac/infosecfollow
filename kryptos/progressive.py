"""Progressive / sliding keys: aperiodic keystreams that every period test is blind to,
yet whose structure is a one-line formula -- exactly "simple algorithm, key with quite a lot of
entropy, but some structure".

  block-progressive : k[i] = key[i%p] + (i//p)*d          (Trithemius/Gronsfeld progressive)
  letter-progressive: k[i] = key[i%p] + i*d
  quadratic         : k[i] = key[i%p] + (i*(i+1)//2)*d

Each has a KNOWN inverse, so subtract the progression and the residue is a plain period-p cipher
that the transposition-invariant column-IoC test can see. Scanning (p,d) turns an aperiodic key
back into a periodic one. Effective period is p*26/gcd(d,26) -- e.g. p=7,d=1 gives 182, far beyond
what any period scan reaches.
"""
import numpy as np, json, sys
from lib import *

def progression(kind, n, p, d):
    i = np.arange(n)
    if kind == 'block':   return (i//p)*d % 26
    if kind == 'letter':  return i*d % 26
    if kind == 'quad':    return (i*(i+1)//2)*d % 26
    raise ValueError(kind)

def colstat(v, p):
    return float(np.mean([ioc(v[r::p]) for r in range(p) if len(v[r::p]) > 3]))

def scan(ct, alpha, kinds, PS, DS, nshuf=200, rng=None):
    rng = rng or np.random.default_rng(999)
    C = to_idx(ct, alpha).astype(int); n = len(C)
    SH = [to_idx(''.join(rng.permutation(list(ct))), alpha).astype(int) for _ in range(nshuf)]
    rows = []
    for kind in kinds:
        for p in PS:
            if n//p < 5: continue
            for d in DS:
                if kind != 'block' and p == 1 and d == 0: continue
                g = progression(kind, n, p, d)
                obs = colstat((C - g) % 26, p)
                nv = np.array([colstat((S - g) % 26, p) for S in SH])
                rows.append({'kind': kind, 'p': int(p), 'd': int(d),
                             'obs': round(obs, 5), 'z': round(float((obs-nv.mean())/nv.std()), 3),
                             'eff_period': int(p*26//np.gcd(d, 26)) if d else int(p)})
    return rows
