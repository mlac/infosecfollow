"""ADVERSARIAL VERIFICATION of the Gromark family claim.
Independent re-implementation (numpy), written from the model description, NOT from gk_kernel.c.
Model (mode 0 / shift-IoC):  score(primer) = IoC( (c[i] + sign*k[i]) mod 26 )
  c[i] = index of ciphertext letter in the chosen TEXT ALPHABET (KA or AZ)
  k    = lagged-recurrence keystream from an L-digit primer, modulus MOD.
"""
import sys, numpy as np
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
from lib import KA, AZ, CT

def ks(primer, n, rec, mod):
    L = len(primer); k = list(primer)
    for i in range(L, n):
        if   rec == 'aca':    v = k[i-L] + k[i-L+1]
        elif rec == 'lag1':   v = k[i-L] + k[i-1]
        elif rec == 'fib':    v = k[i-1] + k[i-2]
        elif rec == 'subaca': v = k[i-L] - k[i-L+1]
        else: raise ValueError(rec)
        k.append(v % mod)
    return k[:n]

def cidx(s, alpha):
    m = {c: i for i, c in enumerate(alpha)}
    return np.array([m[c] for c in s], dtype=np.int64)

def ioc1(v):
    c = np.bincount(np.asarray(v) % 26, minlength=26).astype(np.float64)
    n = len(v)
    return float((c * (c - 1)).sum() / (n * (n - 1)))

def score_one(ct_s, alpha, sign, primer, rec, mod):
    c = cidx(ct_s, alpha)
    k = np.array(ks(primer, len(c), rec, mod), dtype=np.int64)
    return ioc1((c + sign * k) % 26)

# ---------- full 10^L enumeration, vectorised ----------
def enum_best(c, sign, rec, mod, L, topk=8, chunk=100000, ret_hist=False):
    """c: int64 array of ciphertext indices in the text alphabet. Returns (best_score, best_primer, mean, sd)."""
    n = len(c)
    total = mod ** L
    cs = (sign * 1)
    best = -1.0; bestpr = None
    ssum = 0.0; ssq = 0.0
    hist = np.zeros(0)
    hs = []
    # digits of the running primer index -> primer, in the same odometer order (last digit fastest)
    pw = mod ** np.arange(L - 1, -1, -1, dtype=np.int64)
    for start in range(0, total, chunk):
        m = min(chunk, total - start)
        it = np.arange(start, start + m, dtype=np.int64)
        K = np.empty((m, n), dtype=np.int64)
        for j in range(L):
            K[:, j] = (it // pw[j]) % mod
        if rec == 'aca':
            for i in range(L, n): K[:, i] = (K[:, i-L] + K[:, i-L+1]) % mod
        elif rec == 'lag1':
            for i in range(L, n): K[:, i] = (K[:, i-L] + K[:, i-1]) % mod
        elif rec == 'fib':
            for i in range(L, n): K[:, i] = (K[:, i-1] + K[:, i-2]) % mod
        elif rec == 'subaca':
            for i in range(L, n): K[:, i] = (K[:, i-L] - K[:, i-L+1]) % mod
        D = (c[None, :] + cs * K) % 26
        # per-row 26-bin counts via a single bincount over row-offset codes
        off = (np.arange(m, dtype=np.int64) * 26)[:, None]
        cnt = np.bincount((D + off).ravel(), minlength=m * 26).reshape(m, 26).astype(np.float64)
        sc = (cnt * (cnt - 1.0)).sum(axis=1) / (n * (n - 1.0))
        ssum += sc.sum(); ssq += (sc * sc).sum()
        j = int(np.argmax(sc))
        if sc[j] > best:
            best = float(sc[j])
            bestpr = [int((it[j] // pw[q]) % mod) for q in range(L)]
        if ret_hist: hs.append(sc.max())
    mean = ssum / total; sd = (ssq / total - mean * mean) ** 0.5
    return best, bestpr, mean, sd
