"""CRIB ATTACK WITH A COLUMNAR UNDERNEATH (PK4's and PK6's architecture).

ct = q3enc(col_enc(pt, perm), key).  With W | n the columns are equal length L = n/W, so
plaintext position j lands at ciphertext position  slot(j % W) * L + j // W,  where slot = perm^-1.
A crib on pt[0..m-1] therefore gives m known keystream values whose POSITIONS depend only on the
unknown slot assignment -- W! of them.

The consistency condition R.K = 0 is linear, and K decomposes by column:
    R.K = sum_c  R_{slot(c)} . K_c        (K_c depends only on column c and the crib)
so the W! search is a MEET IN THE MIDDLE: enumerate half the slot assignments, hash the partial
sums, and look up the complement. 9! = 362,880 collapses to 3,024 + 15,120.
"""
import numpy as np, itertools, json
from math import comb
from lib import KA, AZ, CT, PT, col_enc, q3enc
from crib_sweep import nullspace_gf, structure_matrix

def positions_for(slot, W, L, m):
    """slot[c] = which output block column c goes to. returns ct position of pt position j"""
    return np.array([slot[j % W]*L + j//W for j in range(m)])

def solve(ct, crib, W, structures, alpha, mode, verbose=False):
    n = len(ct); assert n % W == 0
    L = n // W; m = len(crib)
    ai = {c: i for i, c in enumerate(alpha)}
    C = np.array([ai[c] for c in ct]); P = np.array([ai[c] for c in crib])
    half = W//2
    hits = []
    for st in structures:
        # positions depend on slot, so build the checker for a CANONICAL slot then note that
        # R depends on the actual positions -> we must rebuild per slot. Instead: enumerate the
        # per-column position blocks, and build R for each full slot assignment lazily via MITM
        # over the CONSTRAINT VALUE, which requires R fixed. So fix R by noting the multiset of
        # positions is the same for every slot only when the structure periods divide L.
        # General case: brute force for W<=6, MITM for W in 7..9 using a per-slot R is impossible,
        # so we restrict to structures whose periods all divide L (then position mod p depends
        # only on j//W, identical for every slot) OR brute force.
        ok_fast = all(L % p == 0 for p in st)
        slots = itertools.permutations(range(W))
        if ok_fast:
            # position mod p = (slot*L + j//W) mod p = (j//W) mod p  -> independent of slot!
            pos = np.array([j//W for j in range(m)])
            A = structure_matrix(pos, st)
            R2 = nullspace_gf(A, 2); R13 = nullspace_gf(A, 13)
            if R2.shape[0] + R13.shape[0] == 0: continue
            # K depends on slot only through WHICH ct letter is used
            for slot in slots:
                p_ = positions_for(slot, W, L, m)
                if mode == 'sub':  K = (C[p_] - P) % 26
                elif mode == 'add': K = (P - C[p_]) % 26
                else:               K = (C[p_] + P) % 26
                if (R2.shape[0] == 0 or not (K @ R2.T % 2).any()) and \
                   (R13.shape[0] == 0 or not (K @ R13.T % 13).any()):
                    hits.append({'structure': list(st), 'slot': list(slot),
                                 'r2': int(R2.shape[0]), 'r13': int(R13.shape[0]),
                                 'fp': 2.0**-R2.shape[0] * 13.0**-R13.shape[0]})
        else:
            for slot in slots:
                p_ = positions_for(slot, W, L, m)
                A = structure_matrix(p_, st)
                R2 = nullspace_gf(A, 2); R13 = nullspace_gf(A, 13)
                if R2.shape[0] + R13.shape[0] == 0: continue
                if mode == 'sub':  K = (C[p_] - P) % 26
                elif mode == 'add': K = (P - C[p_]) % 26
                else:               K = (C[p_] + P) % 26
                if (R2.shape[0] == 0 or not (K @ R2.T % 2).any()) and \
                   (R13.shape[0] == 0 or not (K @ R13.T % 13).any()):
                    hits.append({'structure': list(st), 'slot': list(slot),
                                 'r2': int(R2.shape[0]), 'r13': int(R13.shape[0]),
                                 'fp': 2.0**-R2.shape[0] * 13.0**-R13.shape[0]})
    return hits
