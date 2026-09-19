"""SCORER (b) for long periods 25-72: quadgram hill-climb on the period-p additive key.

Model: c[i] = ALPHA[(AI[p[i]] + k[i mod P]) mod 26], k in 0..25^P. Decrypt, map the
alphabet's letters into A-Z index space, score with the quadgram model. Coordinate
descent over the P key slots (each slot's 26 values scored in one vectorised batch),
with random restarts, keeping the best.

LIMITATION, stated plainly: quadgrams are NOT transposition-invariant. If a columnar
sits under the substitution (as it does in PK4, PK5, PK6) this scorer is blind by
construction. PK4 is included below precisely to demonstrate that failure. Scorer (a)
is the one that survives an unknown transposition.

Matched null: the identical hill-climb, identical restart budget, on letter-shuffled
copies of the same ciphertext at the same period.
"""
import numpy as np, sys, time, json
sys.path.insert(0, '.')
from lib import KA, AZ, AZI, CT, load_quadgrams

QG = load_quadgrams()
PERM = {'KA': np.array([AZI[c] for c in KA], dtype=np.int64),
        'AZ': np.arange(26, dtype=np.int64)}
AIDX = {'KA': {c: i for i, c in enumerate(KA)}, 'AZ': {c: i for i, c in enumerate(AZ)}}

def cidx(ct, alpha):
    a = AIDX[alpha]
    return np.array([a[c] for c in ct], dtype=np.int64)

def qrows(A):
    k = A[:, :-3]*17576 + A[:, 1:-2]*676 + A[:, 2:-1]*26 + A[:, 3:]
    return QG[k].mean(axis=1)

def climb(C, P, perm, rng, restarts, sweeps=8, sign=1):
    # sign=+1: additive/Vigenere  d=(c-k).  sign=-1: Beaufort  d=(k-c),
    # reached as (-c-k) over the full k range (k -> -k is a bijection).
    n = len(C); idxmod = np.arange(n) % P
    cand = np.arange(26, dtype=np.int64)
    slots = [np.arange(j, n, P) for j in range(P)]
    best_all = -99.0; bestK = None
    for _ in range(restarts):
        K = rng.integers(0, 26, size=P)
        D = (sign*C - K[idxmod]) % 26
        cur = float(qrows(perm[D][None, :])[0])
        for _s in range(sweeps):
            improved = False
            for j in range(P):
                Pj = slots[j]
                if len(Pj) == 0: continue
                M = np.repeat(perm[D][None, :], 26, axis=0)
                M[:, Pj] = perm[(sign*C[Pj][None, :] - cand[:, None]) % 26]
                sc = qrows(M)
                b = int(np.argmax(sc))
                if sc[b] > cur + 1e-12:
                    cur = float(sc[b]); K[j] = b
                    D[Pj] = (sign*C[Pj] - b) % 26
                    improved = True
            if not improved: break
        if cur > best_all:
            best_all = cur; bestK = K.copy()
    return best_all, bestK

def decrypt(C, K, alpha, sign=1):
    P = len(K); n = len(C)
    D = (sign*C - K[np.arange(n) % P]) % 26
    return ''.join(alpha[int(v)] for v in D)

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'calib'
    rng = np.random.default_rng(11)
    if mode == 'calib':
        # 1) cost, 2) does it recover PK3 (p=40, KA, no transposition)?
        for name, P, alpha, R in [('pk3', 40, 'KA', 40), ('pk4', 45, 'KA', 40),
                                  ('pk10', 40, 'KA', 40), ('pk8', 40, 'KA', 40)]:
            C = cidx(CT[name], alpha)
            t0 = time.time()
            s, K = climb(C, P, PERM[alpha], rng, R)
            dt = time.time() - t0
            pt = decrypt(C, K, KA if alpha == 'KA' else AZ)
            # null
            t1 = time.time()
            nn = [climb(rng.permutation(C), P, PERM[alpha], rng, R)[0] for _ in range(5)]
            print(f"{name} P={P} {alpha} R={R}: obs={s:.4f}  null={np.mean(nn):.4f}+-{np.std(nn):.4f} "
                  f"max={max(nn):.4f}  z={(s-np.mean(nn))/(np.std(nn)+1e-9):+.2f}  "
                  f"{dt:.1f}s/run {(time.time()-t1)/5:.1f}s/null", flush=True)
            print(f"   {pt[:80]}", flush=True)
