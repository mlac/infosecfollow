"""Manufactured long keys: core scoring library.

Model: C[i] = P[i] (op) S[i] on text alphabet ALPHA; S is the manufactured keystream,
whose letters are indexed on KEYALPHA.  mode names follow product2.py:
  'sub'  -> residual R = C - S     (this is the REAL PK1/PK3/PK4 convention)
  'add'  -> R = C + S
  'beau' -> R = S - C
Scoring is IoC only => transposition-invariant (doctrine 3).
"""
import numpy as np, time, json, os
from lib import KA, AZ

def load_words(minL=3, maxL=16, path='words.txt'):
    byl = {}
    for w in open(path).read().split():
        L = len(w)
        if minL <= L <= maxL:
            byl.setdefault(L, []).append(w)
    return byl

def wordmat(words, keyalpha):
    ki = {c: i for i, c in enumerate(keyalpha)}
    return np.array([[ki[c] for c in w] for w in words], dtype=np.int16)

def to_idx(s, alpha):
    ai = {c: i for i, c in enumerate(alpha)}
    return np.array([ai[c] for c in s], dtype=np.int16)

def ioc_rows_fast(R):
    """R: (N,L) int array of values 0..25 -> (N,) IoC."""
    R = np.asarray(R, dtype=np.int64)
    N, L = R.shape
    if L < 2:
        return np.zeros(N)
    off = (np.arange(N, dtype=np.int64) * 26)[:, None]
    cnt = np.bincount((off + R).ravel(), minlength=N * 26).reshape(N, 26).astype(np.float64)
    return (cnt * (cnt - 1)).sum(1) / (L * (L - 1))

def score_parts(C, Wv, parts, mode='sub', off=None, chunk=4000):
    """parts: list of (positions:int array, colmap:int array of same length).
    For each part, peel Wv[:,colmap] (+ optional known offset off[positions]) from C[positions]
    and take IoC.  Returns mean IoC over parts, shape (N,).
    A part is a set of positions on which every OTHER unknown key component is constant."""
    N = Wv.shape[0]
    out = np.zeros(N)
    used = 0
    for pos, cm in parts:
        if len(pos) < 4:
            continue
        used += 1
        Csub = C[pos].astype(np.int16)
        if off is not None:
            Csub = (Csub - off[pos].astype(np.int16)) % 26
        Csub = Csub[None, :]
        cm = np.asarray(cm, dtype=np.int64)
        for s in range(0, N, chunk):
            if cm.ndim == 1:
                W = Wv[s:s + chunk][:, cm]
            else:   # sum of several lookups into the SAME word (progressive keys)
                Wc = Wv[s:s + chunk]
                W = Wc[:, cm[0]].astype(np.int32)
                for row in cm[1:]:
                    W = W + Wc[:, row]
                W = (W % 26).astype(np.int16)
            if mode == 'sub':
                R = (Csub - W) % 26
            elif mode == 'add':
                R = (Csub + W) % 26
            else:
                R = (W - Csub) % 26
            out[s:s + chunk] += ioc_rows_fast(R)
    if used == 0:
        return None
    return out / used

def zstat(sc):
    m, s = float(sc.mean()), float(sc.std())
    b = float(sc.max())
    return b, m, s, ((b - m) / s if s > 0 else 0.0)

def shuffled(ct, rng):
    a = np.frombuffer(ct.encode(), dtype=np.uint8).copy()
    rng.shuffle(a)
    return a.tobytes().decode()

# ---------------- keystream index-map builders ----------------
def map_mod(n, L, a):
    """index map for a word of length a inside a key of length L repeated with period L."""
    i = np.arange(n)
    return ((i % L) % a).astype(np.int64)

def parts_by_group(groupvec, colmap):
    """group positions by the value of groupvec; each part carries its own colmap slice."""
    out = []
    for g in np.unique(groupvec):
        pos = np.nonzero(groupvec == g)[0]
        out.append((pos, colmap[pos]))
    return out

def informative(parts, minvar=2):
    """a part only discriminates if its colmap takes >=2 distinct values."""
    return sum(1 for p, c in parts if len(p) >= 4 and len(np.unique(c)) >= minvar)


def joint_confirm(C, WA, WB, mapA, mapB, idxA, idxB, mode='sub', off=None):
    """Full-length IoC of the decrypt for every (a,b) pair drawn from idxA x idxB.
    Returns (best_ioc, ia, ib, ioc_matrix_max_per_a)."""
    n = len(C)
    SA = WA[idxA][:, mapA].astype(np.int16)
    SB = WB[idxB][:, mapB].astype(np.int16)
    base = C.astype(np.int16)
    if off is not None:
        base = (base - off.astype(np.int16)) % 26
    best = -1.0; bi = bj = -1
    for i in range(SA.shape[0]):
        if mode == 'sub':
            R = (base[None, :] - SA[i][None, :] - SB) % 26
        elif mode == 'add':
            R = (base[None, :] + SA[i][None, :] + SB) % 26
        else:
            R = (SA[i][None, :] + SB - base[None, :]) % 26
        v = ioc_rows_fast(R)
        j = int(v.argmax())
        if v[j] > best:
            best = float(v[j]); bi = i; bj = j
    return best, bi, bj

def keep_informative(parts, minlen=4, minvar=2):
    """Drop parts on which the searched word is constant -- they add a flat offset to every
    candidate and dilute the statistic (this bites hard for depth-3, where most (g2,g3)
    groups pin i%L to a single value)."""
    return [(p, c) for (p, c) in parts if len(p) >= minlen and len(np.unique(c)) >= minvar]
