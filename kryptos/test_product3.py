"""Validate the 3-word solver on synthetics BEFORE trusting its silence (doctrine 2)."""
import numpy as np
from math import lcm
from lib import *
from product3 import *
from product2 import load_words, wordmat, to_idx, score_words
byl = load_words(3,16)
base = (PT['pk2']+PT['pk6']+PT['pk3']+PT['pk7'])

for (n, K, withcol) in [(504, ('OCHRE','VERDIGRIS','ANNEAL'), False),
                        (504, ('OCHRE','VERDIGRIS','ANNEAL'), True),
                        (504, ('PORTAL','ALCHEMIST','UNDERLAY'), False),
                        (153, ('OCHRE','ANVIL','PORTAL'), False),
                        (144, ('OCHRE','ANVIL','PORTAL'), False)]:
    pt = base[:n]
    tr = col_enc(pt, (6,2,3,5,1,4,0,7)) if withcol else pt
    ct = q3enc(tr, list(K))
    C = to_idx(ct, KA); L3 = [len(w) for w in K]
    line = []
    for j, w in enumerate(K):
        a = L3[j]; others = [L3[i] for i in range(3) if i != j]
        M = lcm(*others)
        if M % a == 0 or n//M < 4: line.append(f"{w}:degenerate(M={M})"); continue
        sc = score_words(C, wordmat(byl[a], KA), a, M, 'sub')
        i = byl[a].index(w); r = int(np.where(np.argsort(-sc)==i)[0][0])+1
        line.append(f"{w}(len{a},M={M},cls={n//M}) rank {r}/{len(sc)} z={(sc[i]-sc.mean())/sc.std():+.1f}")
    print(f"n={n} col={withcol} {K}\n   " + " | ".join(line))
