"""Crib + width-9 columnar, by branch-and-bound instead of the infeasible per-permutation nullspace.

Architecture: ct = substitute(col_enc(pt, perm)), width W, n divisible by W, column length L = n/W.
Plaintext position j lands at ciphertext position slot(c)*L + t where c = j%W, t = j//W.
A crib on pt[0..m-1] with m = W*T therefore gives, for each column c and each candidate slot s,
T equations  u[(s*L+t) mod p] = ct[s*L+t] - crib[c + W*t].

Assign columns one at a time; the moment two equations demand different values for the same key
residue, prune. No R is ever built. Degrees of freedom are about m - p, so a 27-letter crib
discriminates for p up to ~20 -- exactly the window that sections F15/F16 show statistics cannot
reach on PK8 and PK9.
"""
import numpy as np

def solve_period(ctv, cribv, W, L, p, mode='sub', limit=200000):
    """ctv, cribv: int arrays. Returns list of (slot tuple, key array) that are fully consistent."""
    T = len(cribv) // W
    if T < 2: return []
    # K[c][s][t]
    K = np.empty((W, W, T), dtype=np.int64)
    for c in range(W):
        for s in range(W):
            for t in range(T):
                a = int(ctv[s*L + t]); b = int(cribv[c + W*t])
                K[c, s, t] = (a - b) % 26 if mode == 'sub' else ((b - a) % 26 if mode == 'add' else (a + b) % 26)
    res = []; nodes = 0
    u = np.full(p, -1, dtype=np.int64)
    used = [False]*W
    def rec(c):
        nonlocal nodes
        if nodes > limit: return
        if c == W:
            res.append((tuple(slot), u.copy())); return
        for s in range(W):
            if used[s]: continue
            nodes += 1
            touched = []
            ok = True
            for t in range(T):
                r = (s*L + t) % p; v = K[c, s, t]
                if u[r] == -1:
                    u[r] = v; touched.append(r)
                elif u[r] != v:
                    ok = False; break
            if ok:
                used[s] = True; slot.append(s)
                rec(c+1)
                slot.pop(); used[s] = False
            for r in touched: u[r] = -1
    slot = []
    rec(0)
    return res, nodes
