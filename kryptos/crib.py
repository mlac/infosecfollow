"""CRIB ATTACK. A crib pins the keystream exactly: K[i] = c[i] - crib[i].
The power is not the crib, it is what the derived keystream must then SATISFY.

If the key is a product k[i] = u[i%a] + v[i%b], then for any "rectangle" of crib positions
i,j,k,l with i=k (mod a), j=l (mod a), i=j (mod b), k=l (mod b), we must have
    K[i] - K[j] - K[k] + K[l] = 0 (mod 26)
Each rectangle is an independent 1-in-26 check, and a 25-letter crib against a (5,9) product
yields about a dozen of them -- a false positive rate near 26^-12. Crucially this needs NO
dictionary: it tests the STRUCTURE of the key, not its vocabulary, which is exactly the setter's
"quite a lot of entropy, but some structure".
"""
import numpy as np, itertools
from math import lcm
from lib import KA, AZ, CT

def rectangles(m, a, b):
    """index quadruples (i,j,k,l) inside a crib of length m that a product key must satisfy"""
    out = []
    pos = range(m)
    byab = {}
    for i in pos: byab.setdefault((i % a, i % b), i)
    for i in pos:
        for k in pos:
            if k <= i or i % b != k % b: continue
            for j in pos:
                if j % a != i % a or j == i: continue
                l = None
                for t in pos:
                    if t % a == k % a and t % b == j % b and t not in (i, j, k): l = t; break
                if l is not None: out.append((i, j, k, l))
    # dedupe and keep an independent-ish subset
    seen = set(); res = []
    for q in out:
        key = tuple(sorted(q))
        if key in seen: continue
        seen.add(key); res.append(q)
    return res

def consistency(K, a, b):
    """returns (n_checks, n_violations) for the product hypothesis k[i]=u[i%a]+v[i%b].
    Solves the bipartite system directly instead of enumerating rectangles: assign u[0]=0, then
    propagate; any conflict is a violation."""
    m = len(K)
    u = {0: 0}; v = {}; checks = 0; viol = 0
    # BFS over the bipartite graph of residues
    order = sorted(range(m), key=lambda i: (i % a, i % b))
    changed = True
    while changed:
        changed = False
        for i in range(m):
            ra, rb = i % a, i % b
            if ra in u and rb not in v: v[rb] = (K[i] - u[ra]) % 26; changed = True
            elif rb in v and ra not in u: u[ra] = (K[i] - v[rb]) % 26; changed = True
    for i in range(m):
        ra, rb = i % a, i % b
        if ra in u and rb in v:
            checks += 1
            if (u[ra] + v[rb]) % 26 != K[i] % 26: viol += 1
    dof = checks - (len(u) + len(v) - 1)          # independent constraints
    return max(dof, 0), viol, u, v

def derive(ct, crib, alpha, mode, off=0):
    ai = {c: i for i, c in enumerate(alpha)}
    C = [ai[c] for c in ct]; P = [ai[c] for c in crib]
    if mode == 'sub':  return [(C[off+i] - P[i]) % 26 for i in range(len(P))]
    if mode == 'add':  return [(P[i] - C[off+i]) % 26 for i in range(len(P))]
    if mode == 'beau': return [(C[off+i] + P[i]) % 26 for i in range(len(P))]

def exact_period(K):
    """smallest p with K[i]==K[i+p] for all valid i, or None"""
    m = len(K)
    for p in range(1, m//2 + 1):
        if all(K[i] == K[i+p] for i in range(m-p)): return p
    return None

# ---------------- general n-factor consistency via CRT ----------------
# Z26 is not a field, but Z26 = GF(2) x GF(13) by CRT, and both ARE fields, so the linear system
# k[i] = sum_f u_f[i mod p_f] can be tested for consistency by Gaussian elimination in each.
def _rank_and_consistent(A, y, q):
    A = [row[:] for row in A]; y = y[:]
    m = len(A); n = len(A[0]) if m else 0
    r = 0
    for c in range(n):
        piv = next((i for i in range(r, m) if A[i][c] % q), None)
        if piv is None: continue
        A[r], A[piv] = A[piv], A[r]; y[r], y[piv] = y[piv], y[r]
        inv = pow(A[r][c], q-2, q)
        A[r] = [(x*inv) % q for x in A[r]]; y[r] = (y[r]*inv) % q
        for i in range(m):
            if i != r and A[i][c] % q:
                f = A[i][c]
                A[i] = [(A[i][j] - f*A[r][j]) % q for j in range(n)]
                y[i] = (y[i] - f*y[r]) % q
        r += 1
        if r == m: break
    for i in range(r, m):
        if all(v % q == 0 for v in A[i]) and y[i] % q: return r, False
    return r, True

def consistency_multi(K, periods):
    """k[i] = sum_f u_f[i mod periods[f]].  Returns (dof, consistent).
    dof = number of independent 1-in-26 checks the crib imposes; higher = more discriminating."""
    m = len(K); offs = []; tot = 0
    for p in periods: offs.append(tot); tot += p
    A = []
    for i in range(m):
        row = [0]*tot
        for f, p in enumerate(periods): row[offs[f] + (i % p)] += 1
        A.append(row)
    ok = True; ranks = []
    for q in (2, 13):
        r, c = _rank_and_consistent(A, [k % q for k in K], q)
        ranks.append(r); ok &= c
    dof = m - max(ranks)
    return dof, ok
