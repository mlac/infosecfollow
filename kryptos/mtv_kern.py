"""Independent numpy re-implementation of the Gromark shift-IoC primer enumeration.
Written from the MODEL description (C[i] = MIX(P[i]) + k[i] mod 26; peel k, measure IoC),
not transcribed from gk_kernel.c.  Used to reproduce claimed scores and to rebuild nulls.
"""
import sys, numpy as np
sys.path.insert(0, '/home/user/infosecfollow/kryptos')

def keystream_batch(P, n, rec, mod):
    """P: (B,L) uint8 primers. returns (B,n) uint8 keystream."""
    B, L = P.shape
    K = np.zeros((B, n), np.uint8)
    K[:, :L] = P
    for i in range(L, n):
        if   rec == 0: v = K[:, i-L].astype(np.int16) + K[:, i-L+1]
        elif rec == 1: v = K[:, i-L].astype(np.int16) + K[:, i-1]
        elif rec == 2: v = K[:, i-1].astype(np.int16) + K[:, i-2]
        else:          v = K[:, i-L].astype(np.int16) - K[:, i-L+1]
        K[:, i] = np.mod(v, mod).astype(np.uint8)
    return K

def ioc_batch(c, K, sign):
    """c: (n,) int8 cipher indices 0..25.  K: (B,n).  IoC of (c + sign*k) mod 26."""
    B, n = K.shape
    D = np.mod(c[None, :].astype(np.int16) + sign * K.astype(np.int16), 26).astype(np.int32)
    D += (np.arange(B, dtype=np.int32) * 26)[:, None]
    H = np.bincount(D.ravel(), minlength=26 * B).reshape(B, 26).astype(np.int64)
    num = (H * (H - 1)).sum(1)
    return num / float(n * (n - 1))

def digits_range(lo, hi, L, mod):
    """primers lo..hi-1 in odometer order: LAST digit fastest (matches an ordinary
    base-`mod` counter written most-significant-first)."""
    idx = np.arange(lo, hi, dtype=np.int64)
    out = np.empty((hi - lo, L), np.uint8)
    for j in range(L - 1, -1, -1):
        out[:, j] = (idx % mod).astype(np.uint8)
        idx //= mod
    return out

def enumerate_full(c, L, mod, rec, sign, topk=8, chunk=200000, total=None):
    n = len(c)
    if total is None:
        total = mod ** L
    bs = -1.0 * np.ones(topk)
    bp = np.zeros((topk, L), np.uint8)
    s = 0.0; ss = 0.0; cnt = 0
    for lo in range(0, total, chunk):
        hi = min(lo + chunk, total)
        P = digits_range(lo, hi, L, mod)
        K = keystream_batch(P, n, rec, mod)
        sc = ioc_batch(c, K, sign)
        s += sc.sum(); ss += (sc * sc).sum(); cnt += sc.size
        m = sc.argsort()[::-1][:topk]
        cs = np.concatenate([bs, sc[m]])
        cp = np.concatenate([bp, P[m]])
        o = cs.argsort()[::-1][:topk]
        bs = cs[o]; bp = cp[o]
    mean = s / cnt; sd = (ss / cnt - mean * mean) ** 0.5
    return {'best': bs, 'primer': bp, 'mean': mean, 'sd': sd, 'count': cnt}

def score_one(c, primer, rec, mod, sign):
    P = np.array([primer], np.uint8)
    K = keystream_batch(P, len(c), rec, mod)
    return float(ioc_batch(c, K, sign)[0]), K[0]
