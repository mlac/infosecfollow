"""Frontier item 1, RUN: crib + width-9 columnar by branch-and-bound, aimed at periods 14-22 --
the window sections F15/F16 show statistics cannot reach on PK8/PK9.
'add' mode is dropped: for a single period p, u -> -u is also a period-p key, so it is redundant
with 'sub' exactly as in F7."""
import numpy as np, json, time, sys
from lib import KA, AZ, CT
from crib_bnb import solve_period
CR=[c[:27] for c in open('cribs_big.txt').read().split() if len(c)>=27]
CR=sorted(set(CR))
W=9; PER=range(14,23)
hits=[]; ntest=0; t0=time.time()
for tag in ('pk8','pk9','pk10'):
    n=len(CT[tag]); L=n//W
    for an,al in (('KA',KA),('AZ',AZ)):
        ai={c:i for i,c in enumerate(al)}
        ctv=np.array([ai[c] for c in CT[tag]])
        for mode in ('sub','beau'):
            for p in PER:
                for cr in CR:
                    cv=np.array([ai[c] for c in cr])
                    r,_=solve_period(ctv,cv,W,L,p,mode)
                    ntest+=1
                    if r:
                        hits.append({'target':tag,'alpha':an,'mode':mode,'p':p,'crib':cr,
                                     'n_slots':len(r),'slot':list(r[0][0])})
            print(f"  {tag} {an} {mode}: cum {ntest:,} tests, {len(hits)} hits ({time.time()-t0:.0f}s)",flush=True)
json.dump({'n_cribs':len(CR),'W':W,'periods':list(PER),'n_tests':ntest,'hits':hits,
           'wall_sec':round(time.time()-t0,1)},open('results/crib_bnb.json','w'),indent=1)
print(f"\n=== CRIB + WIDTH-9 COLUMNAR, BRANCH-AND-BOUND ===")
print(f"  {len(CR):,} distinct 27-letter cribs x periods 14-22 x 3 targets x 2 alphabets x 2 modes")
print(f"  tests executed: {ntest:,}   wall {time.time()-t0:.0f}s   consistent permutations found: {len(hits)}")
for h in hits[:25]: print("   HIT",h)
