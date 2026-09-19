import numpy as np, json, sys, time
from lib import KA, AZ, CT
from product2 import load_words, wordmat, to_idx, score_words
from product3 import moduli
TARGET=sys.argv[1]; NSH=int(sys.argv[2]); MINC=int(sys.argv[3]) if len(sys.argv)>3 else 6
ct=CT[TARGET]; n=len(ct); byl=load_words(3,16)
rng=np.random.default_rng(2718+n)
SHUF=[''.join(rng.permutation(list(ct))) for _ in range(NSH)]
Ms=moduli(3,16,n,MINC)
print(f"{TARGET} n={n}: {len(Ms)} moduli (achievable lcm(b,c) with class size >= {MINC}): {sorted(Ms)}",flush=True)
cells=[]; t00=time.time(); nev=0
for TA,ta in (('KA',KA),('AZ',AZ)):
    C=to_idx(ct,ta); CS=[to_idx(s,ta) for s in SHUF]
    for KN,ka in (('KA',KA),('AZ',AZ)):
        Wc={L:wordmat(byl[L],ka) for L in byl}
        for mode in ('sub','add','beau'):
            t0=time.time()
            for M in sorted(Ms):
                for L in range(3,17):
                    if M%L==0: continue
                    sc=score_words(C,Wc[L],L,M,mode); nev+=len(sc)
                    mu,sd=sc.mean(),sc.std(); o=np.argsort(-sc)[:10]
                    nz=[]
                    for Cx in CS:
                        s2=score_words(Cx,Wc[L],L,M,mode); nev+=len(s2)
                        nz.append(float(((s2-s2.mean())/s2.std()).max()))
                    cells.append({'TA':TA,'KA':KN,'mode':mode,'L':L,'M':M,'bc':Ms[M],
                        'n_words':int(len(sc)),'best_z':float((sc[o[0]]-mu)/sd),
                        'best_ioc':float(sc[o[0]]),'null_mean':float(np.mean(nz)),
                        'null_max':float(np.max(nz)),
                        'top':[[byl[L][i],round(float((sc[i]-mu)/sd),2)] for i in o]})
            print(f"  {TARGET} {TA}/{KN}/{mode}: {time.time()-t0:.0f}s cum {time.time()-t00:.0f}s cells={len(cells)}",flush=True)
json.dump({'target':TARGET,'n':n,'nshuf':NSH,'min_class':MINC,'n_word_evals':nev,
           'wall_sec':round(time.time()-t00,1),'cells':cells},open(f'results/product3_{TARGET}.json','w'))
obs=np.array([c['best_z'] for c in cells]); nmx=np.array([c['null_max'] for c in cells])
print(f"\n=== {TARGET} THREE-WORD: {len(cells)} cells, {nev:,} word-evals, {time.time()-t00:.0f}s ===")
print(f"observed max z {obs.max():.2f} | sweep-wide matched-null ceiling {nmx.max():.2f} -> "
      f"{'ABOVE - AUTOPSY' if obs.max()>nmx.max() else 'BELOW - nothing'}")
print(f"cells beating own null: {(obs>nmx).sum()}/{len(cells)} (chance ~{len(cells)/(NSH+1):.0f})")
for c in sorted(cells,key=lambda c:-c['best_z'])[:10]:
    print(f"  {c['TA']}/{c['KA']}/{c['mode']} L={c['L']} M={c['M']} z={c['best_z']:.2f} "
          f"nullmax={c['null_max']:.2f} top={[t[0] for t in c['top'][:5]]}")
