"""Battery of STRUCTURE tests applied to a crib-derived keystream K (rows of an (N,m) int array).

A crib pins the keystream exactly: K[i] = c[off+i] (-/+) crib[i].  The crib itself is unfalsifiable
-- what is falsifiable is whether the keystream it implies has any structure a key would have.
Every test below is a property of K alone, so the same code runs on real and on shuffled ciphertext
and the null rate is measured, not assumed.

Key-alphabet note: K holds indices into the KEY alphabet.  A key written as English letters is a
word only after mapping those indices through that alphabet, so every word/English test is run
twice, once reading K as KA-indices and once as A-Z indices.
"""
import numpy as np, sys
sys.path.insert(0, '.')
from lib import KA, AZ, KAI, AZI, CT, PT, load_quadgrams, qscore_rows

MAP = {'KA': np.array([AZI[c] for c in KA], dtype=np.int64),      # KA index -> A-Z index
       'AZ': np.arange(26, dtype=np.int64)}

# ---------------------------------------------------------------- dictionary
_W = {}
def words_by_len(path='words.txt', lo=4, hi=13):
    if _W: return _W
    for line in open(path):
        w = line.strip().upper()
        if not w.isalpha() or not (lo <= len(w) <= hi): continue
        _W.setdefault(len(w), []).append(w)
    for L in list(_W):
        a = np.array([[AZI[c] for c in w] for w in _W[L]], dtype=np.int64)
        code = np.zeros(len(a), dtype=np.int64)
        for j in range(L): code = code*26 + a[:, j]
        _W[L] = np.unique(code)
    return _W

def _codes(Kaz, L):
    """base-26 codes of every length-L window of every row. Kaz (N,m) -> (N, m-L+1)"""
    N, m = Kaz.shape
    if m < L: return None
    out = np.zeros((N, m-L+1), dtype=np.int64)
    for j in range(L): out = out*26 + Kaz[:, j:j+m-L+1]
    return out

def isword_cube(Kaz, LS):
    """bool (N, m, len(LS)): is the length-LS[t] window starting at i a dictionary word"""
    W = words_by_len(); N, m = Kaz.shape
    cube = np.zeros((N, m, len(LS)), dtype=bool)
    for t, L in enumerate(LS):
        if m < L or L not in W: continue
        c = _codes(Kaz, L)
        idx = np.searchsorted(W[L], c)
        idx[idx >= len(W[L])] = 0
        cube[:, :m-L+1, t] = (W[L][idx] == c)
    return cube

# ---------------------------------------------------------------- tests
def t_periodic(K, min_checks=5):
    """smallest p with K[i]==K[i+p] everywhere and at least min_checks constraints; -1 if none"""
    N, m = K.shape
    best = np.full(N, -1, dtype=np.int32)
    for p in range(1, m - min_checks + 1):
        ok = (K[:, :m-p] == K[:, p:]).all(axis=1) & (best < 0)
        best[ok] = p
    return best

def t_affine(K):
    """K[i] = a + b*i mod 26 (progressive / Trithemius key)"""
    if K.shape[1] < 5: return np.zeros(len(K), bool)
    return ((K[:, 2:] - 2*K[:, 1:-1] + K[:, :-2]) % 26 == 0).all(axis=1)

def t_fib(K):
    """K[i] = K[i-1] + K[i-2] mod 26 (lagged recurrence key)"""
    if K.shape[1] < 6: return np.zeros(len(K), bool)
    return ((K[:, 2:] - K[:, 1:-1] - K[:, :-2]) % 26 == 0).all(axis=1)

def t_words(cube, LS):
    """(w1, w2, seg): a long word anywhere; two adjacent words; a full segmentation"""
    N, m, T = cube.shape
    li = {L: t for t, L in enumerate(LS)}
    long_ = [li[L] for L in LS if L >= 8]
    w1 = cube[:, :, long_].any(axis=(1, 2)) if long_ else np.zeros(N, bool)
    w2 = np.zeros(N, bool)
    for L1 in LS:
        if L1 < 6: continue
        for i in range(m - L1):
            second = [li[L2] for L2 in LS if L2 >= 6 and i + L1 + L2 <= m]
            if not second: continue
            w2 |= cube[:, i, li[L1]] & cube[:, i+L1, second].any(axis=1)
    reach = np.zeros((N, m+1), dtype=bool); reach[:, 0] = True
    for i in range(m):
        for L in LS:
            if i + L <= m: reach[:, i+L] |= reach[:, i] & cube[:, i, li[L]]
    return w1, w2, reach[:, m]

_SIB = {}
def sibling_codes(L=12):
    """base-26 codes of every L-gram of every solved plaintext/ciphertext, per key alphabet"""
    if L in _SIB: return _SIB[L]
    out = {}
    for an, ai in (('KA', KAI), ('AZ', AZI)):
        cs = []
        for src in list(PT.values()) + list(CT.values()):
            v = np.array([ai[c] for c in src], dtype=np.int64)
            for s in (v, v[::-1]):
                if len(s) < L: continue
                c = np.zeros(len(s)-L+1, dtype=np.int64)
                for j in range(L): c = c*26 + s[j:len(s)-L+1+j]
                cs.append(c)
        out[an] = np.unique(np.concatenate(cs))
    _SIB[L] = out
    return out

def t_running_sibling(K, keyalpha, L=12):
    """is K a literal window of a solved sibling text (the PK5 construction)?"""
    N, m = K.shape
    if m < L: return np.zeros(N, bool)
    S = sibling_codes(L)[keyalpha]
    c = _codes(K.astype(np.int64), L)
    idx = np.searchsorted(S, c); idx[idx >= len(S)] = 0
    return (S[idx] == c).any(axis=1)

def t_english(Kaz, qg=None):
    """quadgram log10/letter of the keystream read as English (running-key hypothesis)"""
    if Kaz.shape[1] < 4: return np.full(len(Kaz), -99.0)
    return qscore_rows(Kaz, qg)
