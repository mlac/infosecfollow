"""DOCTRINE: validate the solver recovers a synthetic instance before trusting its silence."""
import numpy as np, time
from lib import *
from product2 import *

byl = load_words()
np.random.seed(7)

def synth(n):
    """504-letter plaintext in the series' own register."""
    s = (PT['pk2'] + PT['pk6'] + PT['pk3'])
    return s[:n]

for (n, A, B, mode) in [(504, 'OCHRE', 'VERDIGRIS', 'sub'),
                        (504, 'CRUCIBLE', 'FILIGREE', 'sub'),
                        (153, 'OCHRE', 'VERDIGRIS', 'sub'),
                        (144, 'ANVIL', 'QUENCHING', 'sub')]:
    pt = synth(n)
    # PK4's exact construction: columnar first, then the product substitution.
    W = 8; perm = (6,2,3,5,1,4,0,7)
    tr = col_enc(pt[:len(pt)//W*W], perm)
    tr = (tr + pt[len(tr):])[:n]
    ct = q3enc(tr, [A, B])
    a, b = len(A), len(B)
    C = to_idx(ct, KA)
    scA = score_words(C, wordmat(byl[a], KA), a, b, mode)
    scB = score_words(C, wordmat(byl[b], KA), b, a, mode)
    rA = int(np.where(np.argsort(-scA) == byl[a].index(A))[0][0]) + 1
    rB = int(np.where(np.argsort(-scB) == byl[b].index(B))[0][0]) + 1
    zA = (scA[byl[a].index(A)]-scA.mean())/scA.std()
    zB = (scB[byl[b].index(B)]-scB.mean())/scB.std()
    print(f"n={n} {A}({a})x{B}({b}) mode={mode}: "
          f"{A} rank {rA}/{len(scA)} z={zA:.1f} | {B} rank {rB}/{len(scB)} z={zB:.1f}")
