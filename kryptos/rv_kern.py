"""rv_kern.py -- INDEPENDENT numpy re-implementation of the Gromark shift-IoC search.

Written from the model description in the claim, NOT from gk_kernel.c:
    C[i] = MIX(P[i]) + k[i]  (mod 26)
    score(primer) = IoC of  (c[i] + sign*k[i]) mod 26,  c read in a given text alphabet.
k[] from an L-digit primer by one of four recurrences, modulus `mod`.
"""
import sys, numpy as np
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
from lib import KA, AZ, CT

RECS = ('aca', 'lag1', 'fib', 'subaca')

def to_ct_idx(s, alpha):
    ai = {c: i for i, c in enumerate(alpha)}
    return np.array([ai[c] for c in s], dtype=np.int16)

def keystream_rows(P, n, rec, mod):
    """P: (B,L) uint8 primers -> (B,n) uint8 keystream."""
    B, L = P.shape
    K = np.zeros((B, n), dtype=np.uint8)
    K[:, :L] = P
    for i in range(L, n):
        if   rec == 'aca':    v = K[:, i-L].astype(np.int16) + K[:, i-L+1]
        elif rec == 'lag1':   v = K[:, i-L].astype(np.int16) + K[:, i-1]
        elif rec == 'fib':    v = K[:, i-1].astype(np.int16) + K[:, i-2]
        elif rec == 'subaca': v = K[:, i-L].astype(np.int16) - K[:, i-L+1]
        else: raise ValueError(rec)
        K[:, i] = np.mod(v, mod).astype(np.uint8)
    return K

def score_rows(c, K, sign):
    """c: (n,) int16 letter indices 0..25. K: (B,n) uint8. -> (B,) IoC."""
    B, n = K.shape
    if sign > 0: V = (c[None, :] + K).astype(np.int32)
    else:        V = (c[None, :] + 26 - K).astype(np.int32)
    V %= 26
    V += (np.arange(B, dtype=np.int32) * 26)[:, None]
    cnt = np.bincount(V.ravel(), minlength=26*B).reshape(B, 26).astype(np.int64)
    num = (cnt * (cnt - 1)).sum(1)
    return num / float(n * (n - 1))

def enumerate_full(c, L, mod, rec, sign, chunk=100000, topk=8, progress=None):
    """Full mod**L enumeration. Returns (topk scores, topk primers, mean, sd, count)."""
    n = len(c)
    total = mod ** L
    best_s = np.full(topk, -1.0); best_p = np.zeros((topk, L), np.uint8)
    s1 = 0.0; s2 = 0.0; cnt = 0
    pw = (mod ** np.arange(L - 1, -1, -1)).astype(np.int64)
    for start in range(0, total, chunk):
        stop = min(start + chunk, total)
        ii = np.arange(start, stop, dtype=np.int64)
        P = ((ii[:, None] // pw[None, :]) % mod).astype(np.uint8)
        K = keystream_rows(P, n, rec, mod)
        sc = score_rows(c, K, sign)
        s1 += sc.sum(); s2 += (sc * sc).sum(); cnt += sc.size
        m = min(topk, sc.size)
        loc = np.argpartition(-sc, m - 1)[:m]
        cs = np.concatenate([best_s, sc[loc]]); cp = np.concatenate([best_p, P[loc]])
        o = np.argsort(-cs)[:topk]
        best_s, best_p = cs[o], cp[o]
        if progress and (start // chunk) % progress == 0:
            print("  %d/%d best=%.6f" % (stop, total, best_s[0]), flush=True)
    mean = s1 / cnt; sd = (s2 / cnt - mean * mean) ** 0.5
    return best_s, best_p, mean, sd, cnt

def score_primer(c, primer, mod, rec, sign):
    P = np.array([primer], dtype=np.uint8)
    K = keystream_rows(P, len(c), rec, mod)
    return float(score_rows(c, K, sign)[0]), K[0]
