"""Frontier item 3: THREE-word product keys, dictionary-wide.

c[i] = p[i] + k1[i%a] + k2[i%b] + k3[i%c].  Peel the correct k1 and every residue class mod
M=lcm(b,c) is MONOALPHABETIC (k2 and k3 are both constant inside it).  So the score for a
length-a word depends on b,c ONLY through M -> the triple search collapses to a (length, modulus)
grid.  Signal requires a does not divide M.  Survives an unknown columnar transposition.
"""
import numpy as np, json, sys, time
from math import lcm
from lib import KA, AZ, CT, PT, ioc, col_enc, q3enc
from product2 import load_words, wordmat, to_idx, score_words

def moduli(minL=3, maxL=16, n=504, min_class=6):
    """achievable lcm(b,c) for 3<=b<=c<=maxL, keeping classes big enough to measure IoC"""
    s = {}
    for b in range(minL, maxL+1):
        for c in range(b, maxL+1):
            M = lcm(b, c)
            if M <= n // min_class:
                s.setdefault(M, []).append((b, c))
    return s

def grid(ct, byl, textalpha, keyalpha, mode, min_class=6, maxL=16, topk=15, nulls=None):
    C = to_idx(ct, textalpha); n = len(ct)
    Ms = moduli(3, maxL, n, min_class)
    Wc = {L: wordmat(byl[L], keyalpha) for L in byl}
    rows = []
    for M in sorted(Ms):
        for L in range(3, maxL+1):
            if M % L == 0: continue                     # no decomposition signal
            sc = score_words(C, Wc[L], L, M, mode)
            mu, sd = sc.mean(), sc.std()
            o = np.argsort(-sc)[:topk]
            r = {'M': M, 'L': L, 'pairs_bc': Ms[M], 'n_words': int(len(sc)),
                 'best_z': float((sc[o[0]]-mu)/sd), 'best_ioc': float(sc[o[0]]),
                 'mu': float(mu), 'sd': float(sd),
                 'top': [[byl[L][i], round(float((sc[i]-mu)/sd), 2)] for i in o]}
            if nulls is not None:
                nz = []
                for Cx in nulls:
                    s2 = score_words(Cx, Wc[L], L, M, mode)
                    nz.append(float(((s2-s2.mean())/s2.std()).max()))
                r['null_mean'] = float(np.mean(nz)); r['null_max'] = float(np.max(nz))
            rows.append(r)
    return rows
