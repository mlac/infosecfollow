"""DOCTRINE 2 AT THE SWEEP LEVEL. The PK8/PK9 two-word product negatives are only Tier 2 if the
IDENTICAL grid, run on a message of the same length that really does have a two-word product key,
reports ABOVE CEILING. Synthetic controls at the cell level gave z=4.8-6.3 at n=153 while the
sweep-wide ceiling was 7.87 -- so this needs checking, and the answer may force a downgrade."""
import numpy as np, json, sys, time
from lib import *
from product2 import load_words, wordmat, to_idx as p2_idx, score_words, pairs
byl = load_words(3,16); PL = pairs(3,16)
ENG = (PT['pk2']+PT['pk6']+PT['pk3']+PT['pk7'])
n = int(sys.argv[1]); A, B = sys.argv[2], sys.argv[3]
CEIL = float(sys.argv[4])
pt = ENG[:n]
ct = q3enc(col_enc(pt,(6,2,3,5,1,4,0,7))[:n], [A,B])
rng = np.random.default_rng(555)
SH = [''.join(rng.permutation(list(ct))) for _ in range(5)]
best = -9; bestcell = None; t0=time.time()
truez = {}
for TA,ta in (('KA',KA),('AZ',AZ)):
    C = p2_idx(ct,ta); CS=[p2_idx(s,ta) for s in SH]
    for KN,ka in (('KA',KA),('AZ',AZ)):
        Wc={L:wordmat(byl[L],ka) for L in byl}
        for mode in ('sub','add','beau'):
            for (a,b) in PL:
                for d,L,m in (('A',a,b),('B',b,a)):
                    if d=='A' and b%a==0: continue
                    sc=score_words(C,Wc[L],L,m,mode)
                    z=float((sc.max()-sc.mean())/sc.std())
                    if z>best: best=z; bestcell=(TA,KN,mode,a,b,d,byl[L][int(sc.argmax())])
                    if TA=='KA' and KN=='KA' and mode=='sub':
                        for w in (A,B):
                            if len(w)==L and w in byl[L]:
                                i=byl[L].index(w)
                                truez.setdefault(w,[]).append(((a,b,d),round(float((sc[i]-sc.mean())/sc.std()),2)))
print(f"synthetic n={n}, true key {A}({len(A)}) x {B}({len(B)}), columnar W8 underneath, {time.time()-t0:.0f}s")
print(f"  sweep-wide observed max z = {best:.2f}  at {bestcell}")
print(f"  real-sweep ceiling for this length = {CEIL:.2f}")
print(f"  -> the sweep {'WOULD have detected' if best>CEIL else 'WOULD NOT have detected'} this key")
for w,v in truez.items():
    v.sort(key=lambda t:-t[1]); print(f"  true key {w}: best cell z {v[0]}")
