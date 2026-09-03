"""Frontier item 4's missing piece: the crib x key-structure sweep applied to the DERIVED texts.
If PK8's key is PK9's plaintext then d = c8 - c9 is PK8's plaintext under PK9's keystream, so a
crib on PK8's plaintext against d tests PK9's key structure directly."""
import numpy as np, itertools, json, time
from lib import KA, AZ
from derived import derived_texts
from crib_sweep import build_cribs, make_checker

CR = build_cribs(); D = derived_texts()
STR  = [(p,) for p in range(2,25)]
STR += [(a,b) for a in range(3,17) for b in range(a+1,17)]
STR += [t for t in itertools.combinations(range(3,15),3)]
MAXFP = 1e-6
CK = {}; hits=[]; ntest=0; efp=0.0; t0=time.time()
for tag,(s,an) in D.items():
    al = KA if an=='KA' else AZ
    ai = {c:i for i,c in enumerate(al)}
    Cv = np.array([ai[c] for c in s]); n=len(s)
    for mode in ('sub','add','beau'):
        for at_end in (False,True):
            for m in sorted({len(c) for c in CR}):
                subs=[c for c in CR if len(c)==m]
                P=np.array([[ai[ch] for ch in c] for c in subs])
                pos = np.arange(n-m,n) if at_end else np.arange(m)
                Cs = Cv[pos][None,:]
                K = (Cs-P)%26 if mode=='sub' else ((P-Cs)%26 if mode=='add' else (Cs+P)%26)
                for st in STR:
                    key=(tuple(pos),st)
                    if key not in CK: CK[key]=make_checker(pos,st)
                    R2,R13,r2,r13=CK[key]
                    fp=(2.0**-r2)*(13.0**-r13)
                    if fp>MAXFP: continue
                    ok=np.ones(len(subs),bool)
                    if r2:  ok &= ((K@R2.T)%2==0).all(1)
                    if r13: ok &= ((K@R13.T)%13==0).all(1)
                    ntest+=len(subs); efp+=fp*len(subs)
                    for i in np.nonzero(ok)[0]:
                        hits.append({'text':tag,'mode':mode,'at_end':at_end,
                                     'crib':subs[i],'structure':list(st),'fp':fp})
    print(f"  {tag}: cum {ntest:,} tests, {len(hits)} hits ({time.time()-t0:.0f}s)",flush=True)
json.dump({'n_tests':ntest,'expected_fp':efp,'hits':hits},open('results/crib_derived.json','w'),indent=1)
print(f"\n=== CRIB SWEEP ON 48 DERIVED COUPLING TEXTS ===")
print(f"  effective tests: {ntest:,}   expected false positives: {efp:.2e}   observed passes: {len(hits)}")
for h in hits[:30]: print("   HIT",h)
