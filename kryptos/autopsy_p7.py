"""AUTOPSY of the only surviving period flag: PK8 p=7 (obs z=+3.25), PK8 p=14 (+2.23),
PK9 p=7 (+2.41), PK9 p=14 (+1.84). Two independent solvers, each with a matched null."""
import numpy as np
from lib import *
rng = np.random.default_rng(808)
ENG = ''.join(PT[k] for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7'])
QG = np.load('quadgrams.npy')

def solve_quadgram(ct, p, alpha=KA, restarts=60):
    """assumes NO transposition"""
    C = to_idx(ct, alpha).astype(int); n = len(C); best = (-99, None)
    for _ in range(restarts):
        k = rng.integers(0, 26, p)
        cur = qscore(ka_to_az(to_str((C-k[np.arange(n)%p])%26, alpha)), QG)
        improved = True
        while improved:
            improved = False
            for r in range(p):
                for v in range(26):
                    if v == k[r]: continue
                    k2 = k.copy(); k2[r] = v
                    s = qscore(ka_to_az(to_str((C-k2[np.arange(n)%p])%26, alpha)), QG)
                    if s > cur: cur, k, improved = s, k2, True
        if cur > best[0]: best = (cur, k.copy())
    return best

def solve_mutual_ioc(ct, p, alpha=KA, restarts=40):
    """transposition-INVARIANT: align the p column histograms by shift to maximise pooled IoC"""
    C = to_idx(ct, alpha).astype(int); n = len(C); best = (-1, None)
    H = np.array([np.bincount(C[r::p], minlength=26) for r in range(p)], dtype=float)
    for _ in range(restarts):
        s = rng.integers(0, 26, p); s[0] = 0
        for _ in range(80):
            pooled = sum(np.roll(H[r], -s[r]) for r in range(p))
            ch = False
            for r in range(p):
                rest = pooled - np.roll(H[r], -s[r])
                sc = [ (rest*np.roll(H[r], -v)).sum() for v in range(26) ]
                v = int(np.argmax(sc))
                if v != s[r]: s[r] = v; pooled = rest + np.roll(H[r], -v); ch = True
            if not ch: break
        tot = sum(np.roll(H[r], -s[r]) for r in range(p)); N = tot.sum()
        v = (tot*(tot-1)).sum()/(N*(N-1))
        if v > best[0]: best = (v, s.copy())
    return best

for tag, p in (('pk8',7), ('pk8',14), ('pk9',7), ('pk9',14)):
    ct = CT[tag]; n = len(ct)
    q, kq = solve_quadgram(ct, p)
    m, km = solve_mutual_ioc(ct, p)
    NQ, NM = [], []
    for _ in range(25):
        s = ''.join(rng.permutation(list(ct)))
        NQ.append(solve_quadgram(s, p)[0]); NM.append(solve_mutual_ioc(s, p)[0])
    dec = to_str((to_idx(ct)-kq[np.arange(n)%p])%26)
    print(f"\n--- {tag} period {p} ---")
    print(f"  quadgram solve (no-transposition assumption): {q:.3f}  "
          f"matched null mean {np.mean(NQ):.3f} max {np.max(NQ):.3f}  -> "
          f"{'ABOVE' if q>np.max(NQ) else 'BELOW'} ceiling   (English = -4.25)")
    print(f"  mutual-IoC solve (transposition-invariant)  : {m:.4f}  "
          f"matched null mean {np.mean(NM):.4f} max {np.max(NM):.4f}  -> "
          f"{'ABOVE' if m>np.max(NM) else 'BELOW'} ceiling   (English = 0.065)")
    print(f"  best key (KA letters): {to_str(kq)}")
    print(f"  decrypt: {dec[:80]}")
