import numpy as np, random
from crib_multiset import test
from lib import *
random.seed(3); rng=np.random.default_rng(3)
ENG=''.join(PT[k] for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7'])
print("=== POSITIVE CONTROL: synthetic 'columnar W then key period dividing L' ===")
for (n,W) in ((153,9),(144,9),(504,9),(144,8),(504,7)):
    L=n//W; pt=ENG[:n]; perm=list(rng.permutation(W)); u=rng.integers(0,26,L)
    ct=to_str((to_idx(col_enc(pt,perm))+u[np.arange(n)%L])%26)
    r=test(ct,pt[:3*W],W,KA,'sub')
    print(f"  n={n} W={W} L={L}: fires={r is not None} shifts/t={[len(x) for x in r] if r else None}")
print("=== MATCHED NULL: random cribs ===")
for W,mlen in ((9,27),(8,24),(7,21),(3,18)):
    bad=tot=0
    for _ in range(8000):
        fake=''.join(random.choice(KA) for _ in range(mlen)); tot+=1
        if test(CT['pk9' if 144%W==0 else 'pk10'],fake,W,KA,'sub'): bad+=1
    print(f"  W={W} crib len {mlen}: {bad}/{tot} random cribs pass ({bad/tot*100:.3f}%)")
