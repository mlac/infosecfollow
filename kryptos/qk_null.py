"""Rebuilt-from-scratch matched null for the concat/interleave claimed hit on pk9.
usage: python3 qk_null.py <mode: shuffle|relabel> <ndraws> <seed>
Unit of comparison = per (draw, config, kind) run maximum over the 100-cell (a,b) grid,
the identical statistic the family reported for the real ciphertext."""
import sys,json,time; sys.path.insert(0,'.')
import numpy as np
from lib import KA,AZ,CT,ioc
import mk_lib as M, qk_core as Q

mode=sys.argv[1]; ND=int(sys.argv[2]); SEED=int(sys.argv[3])
byl=M.load_words(Q.AMIN,Q.AMAX)
WM={ka:{L:M.wordmat(byl[L],Q.ALPH[ka]) for L in byl} for ka in ('KA','AZ')}
WMR={ka:{L:WM[ka][L][:,::-1].copy() for L in byl} for ka in ('KA','AZ')}
rng=np.random.default_rng(SEED)
base=CT['pk9']
allruns=[]; tot=0; t00=time.time()
for d in range(ND):
    ct=M.shuffled(base,rng) if mode=='shuffle' else Q.relabel(base,rng)
    t0=time.time()
    runs,cells=Q.run_text(ct,byl,WM,WMR,tag=f'{mode}{d}')
    for r in runs: r['draw']=d; r['ct_ioc']=round(ioc(ct),5)
    allruns+=runs; tot+=cells
    mx=max(r['joint'] for r in runs)
    print(f"[{mode}] draw {d} ct_ioc={ioc(ct):.5f} max={mx:.5f} cells={cells} {time.time()-t0:.0f}s",flush=True)
    json.dump({'mode':mode,'ndraws_done':d+1,'cells':tot,'wall':round(time.time()-t00,1),
               'runs':allruns},open(f'results/qk_null_{mode}.json','w'),indent=1)
print('DONE',mode,'cells',tot,'wall',round(time.time()-t00,1))
