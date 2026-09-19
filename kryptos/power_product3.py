"""§A0 applied to the THREE-word grid: run the identical grid on a 504-letter synthetic that really
has a three-word product key, and ask whether the sweep-wide max beats the ceiling the real PK10
grid produces. Without this the PK10 three-word result cannot be graded Tier 2."""
import numpy as np, sys, time, json
from math import lcm
from lib import KA, AZ, PT, q3enc, col_enc
from product2 import load_words, wordmat, to_idx as p2_idx, score_words
from product3 import moduli
K=tuple(sys.argv[1:4]); n=504
byl=load_words(3,16)
ENG=(PT['pk2']+PT['pk6']+PT['pk3']+PT['pk7'])[:n]
ct=q3enc(col_enc(ENG,(6,2,3,5,1,4,0,7))[:n], list(K))
rng=np.random.default_rng(31)
SH=[''.join(rng.permutation(list(ct))) for _ in range(3)]
Ms=moduli(3,16,n,6)
best=-9; bestcell=None; truez={}
t0=time.time()
for TA,ta in (('KA',KA),('AZ',AZ)):
    C=p2_idx(ct,ta); CS=[p2_idx(s,ta) for s in SH]
    for KN,ka in (('KA',KA),('AZ',AZ)):
        Wc={L:wordmat(byl[L],ka) for L in byl}
        for mode in ('sub','add'):            # beau == sub under this statistic (F7)
            for M in sorted(Ms):
                for L in range(3,17):
                    if M%L==0: continue
                    sc=score_words(C,Wc[L],L,M,mode)
                    z=float((sc.max()-sc.mean())/sc.std())
                    if z>best: best=z; bestcell=(TA,KN,mode,L,M,byl[L][int(sc.argmax())])
                    if TA=='KA' and KN=='KA' and mode=='sub':
                        for w in K:
                            if len(w)==L and w in byl[L]:
                                i=byl[L].index(w)
                                truez.setdefault(w,[]).append((M,round(float((sc[i]-sc.mean())/sc.std()),2)))
print(f"synthetic n={n}, true key {K[0]}({len(K[0])}) x {K[1]}({len(K[1])}) x {K[2]}({len(K[2])}), columnar W8 underneath")
print(f"  {time.time()-t0:.0f}s; sweep-wide observed max z = {best:.2f} at {bestcell}")
for w,v in truez.items():
    v.sort(key=lambda t:-t[1]); print(f"  true key {w}: best cell (M={v[0][0]}) z={v[0][1]}")
json.dump({'key':list(K),'sweep_max':best,'cell':list(map(str,bestcell)),'true':truez},
          open('results/power_product3.json','w'),indent=1)
