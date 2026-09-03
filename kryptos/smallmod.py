"""Small-modulus lagged-Fibonacci keystreams — the direct follow-up to §G2.

§G2 measures PK9's keystream at about FIVE effective cipher alphabets (ML k=5, credible 3-14), and
independently k=5 fits its IoC best (z=+0.20; k=26 is excluded at +3.26). A Gromark-style recurrence
taken mod m yields a keystream over exactly m distinct values, so m=4..7 is precisely the right
shape — and the Gromark family covered only mod 10 and mod 26, so this is untested.

keystream:  k[i] = primer[i]              i < L
            k[i] = (k[i-L] + k[i-L+1]) % m   (or k[i-L]+k[i-1])
shift:      s[i] = d * k[i]  (mod 26), d coprime to 26 so the shift set keeps m distinct values.
A constant offset is absorbed because IoC is shift-invariant, so it need not be searched.
Lever: the correct primer leaves a MONOALPHABETIC residual, so IoC jumps without knowing anything
about the plaintext alphabet, and it survives a columnar transposition underneath.
"""
import numpy as np, itertools
from lib import KA, AZ, CT, to_idx, ioc

def keystreams(m, L, rec):
    """all m^L primers -> (m^L, n) keystream matrix, generated vectorised"""
    P = np.array(list(itertools.product(range(m), repeat=L)), dtype=np.int64)
    return P

def run_cell(C, m, L, rec, ds, n, chunk=40000):
    P = keystreams(m, L, rec)
    best = (-1, None, None); ncfg = 0
    for s0 in range(0, len(P), chunk):
        Pc = P[s0:s0+chunk]
        K = np.zeros((len(Pc), n), dtype=np.int16)
        K[:, :min(L, n)] = Pc[:, :min(L, n)]
        for i in range(L, n):
            if rec == 'aca':  K[:, i] = (K[:, i-L] + K[:, i-L+1]) % m
            else:             K[:, i] = (K[:, i-L] + K[:, i-1]) % m
        for d in ds:
            R = (C[None, :].astype(np.int16) - d*K) % 26
            cnt = np.zeros((len(Pc), 26), dtype=np.int32)
            for x in range(26): cnt[:, x] = (R == x).sum(1)
            io = (cnt.astype(np.float64)*(cnt-1)).sum(1)/(n*(n-1))
            j = int(io.argmax()); ncfg += len(Pc)
            if io[j] > best[0]: best = (float(io[j]), d, tuple(Pc[j].tolist()))
    return best, ncfg
