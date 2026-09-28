"""Two-word product key sweep, decomposed.

Model: c[i] = p[i] (+/-) k1[i%a] (+/-) k2[i%b]   (PK4's construction: OCHRE(5)+VERDIGRIS(9))
Key identity: peel the correct k1 and every residue class mod b becomes MONOALPHABETIC
(k2 is constant inside a class mod b), so its IoC jumps to English regardless of k2 and
regardless of any columnar transposition sitting underneath. That decouples the search:
N_a + N_b candidates instead of N_a * N_b.
Signal exists for the length-a direction only when a does NOT divide b.
"""
import numpy as np, sys, time, json, os
from math import gcd
from lib import KA, AZ, KAI, AZI, CT, PT

def load_words(minL=3, maxL=16):
    ws = open('words.txt').read().split()
    byl = {}
    for w in ws:
        if minL <= len(w) <= maxL:
            byl.setdefault(len(w), []).append(w)
    return byl

def wordmat(words, keyalpha):
    ki = {c: i for i, c in enumerate(keyalpha)}
    return np.array([[ki[c] for c in w] for w in words], dtype=np.int16)

def to_idx(s, alpha):
    ai = {c: i for i, c in enumerate(alpha)}
    return np.array([ai[c] for c in s], dtype=np.int16)

def ioc_rows_fast(R):
    N, L = R.shape
    off = (np.arange(N, dtype=np.int64) * 26)[:, None]
    cnt = np.bincount((off + R).ravel(), minlength=N*26).reshape(N, 26).astype(np.float64)
    return (cnt * (cnt - 1)).sum(1) / (L * (L - 1))

def score_words(Cidx, Wv, a, m, mode, chunk=6000):
    """mean over residue classes mod m of IoC after peeling a length-a key."""
    n = len(Cidx); N = Wv.shape[0]
    out = np.zeros(N)
    for r in range(m):
        P = np.arange(r, n, m)
        if len(P) < 3: continue
        colmap = (P % a).astype(np.int64)
        Csub = Cidx[P].astype(np.int16)[None, :]
        for s in range(0, N, chunk):
            W = Wv[s:s+chunk][:, colmap]
            if mode == 'sub':   R = (Csub - W) % 26
            elif mode == 'add': R = (Csub + W) % 26
            else:               R = (W - Csub) % 26
            out[s:s+chunk] += ioc_rows_fast(R.astype(np.int64))
    return out / m

def pairs(minL=3, maxL=16):
    return [(a, b) for a in range(minL, maxL) for b in range(a+1, maxL+1)]

def sweep(ct, byl, textalpha, keyalpha, mode, plist, topk=25, log=None):
    C = to_idx(ct, textalpha)
    Wcache = {L: wordmat(byl[L], keyalpha) for L in byl}
    res = []
    for (a, b) in plist:
        t0 = time.time()
        row = {'a': a, 'b': b}
        # direction A: score length-a words via classes mod b (needs a not| b)
        if b % a != 0:
            sc = score_words(C, Wcache[a], a, b, mode)
            o = np.argsort(-sc)[:topk]
            row['A'] = {'n': int(len(sc)), 'best': float(sc[o[0]]),
                        'mean': float(sc.mean()), 'sd': float(sc.std()),
                        'top': [(byl[a][i], round(float(sc[i]), 5)) for i in o]}
        # direction B: score length-b words via classes mod a (always has signal)
        sc = score_words(C, Wcache[b], b, a, mode)
        o = np.argsort(-sc)[:topk]
        row['B'] = {'n': int(len(sc)), 'best': float(sc[o[0]]),
                    'mean': float(sc.mean()), 'sd': float(sc.std()),
                    'top': [(byl[b][i], round(float(sc[i]), 5)) for i in o]}
        row['sec'] = round(time.time()-t0, 1)
        res.append(row)
        if log:
            zA = (row['A']['best']-row['A']['mean'])/row['A']['sd'] if 'A' in row else float('nan')
            zB = (row['B']['best']-row['B']['mean'])/row['B']['sd']
            print(f"  ({a:2d},{b:2d}) A z={zA:6.2f} B z={zB:6.2f}  {row['sec']}s", flush=True)
    return res
