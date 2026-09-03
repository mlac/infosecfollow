"""MATCHED NULL, rebuilt from scratch.
Statistic = max decrypt-IoC over the COMPLETE M-A search (all 8 alphabet/mode configs x
696 constructions x every dictionary word of that length) -- exactly the statistic that
produced the real 0.06313 on pk9. Each replicate is a uniform random permutation of the
pk9 ciphertext, which preserves its letter multiset EXACTLY (hence its raw IoC 0.04448,
z=+3.2) and destroys only positional structure. Byte-identical search code to the real run.
usage: python3 adm_null_shuffle.py <tag> <seed> <nrep>
"""
import sys, json, time; sys.path.insert(0,'.')
import numpy as np
import adm_engine as E
from lib import CT

TAG=sys.argv[1]; SEED=int(sys.argv[2]); NREP=int(sys.argv[3])
eng=E.Engine()
rng=np.random.default_rng(SEED)
base=CT['pk9']
rows=[]; t00=time.time()
for r in range(NREP):
    ct=E.shuffled(base,rng)
    t0=time.time()
    res=eng.run(ct)
    rows.append({'rep':r,'grid_max':res['grid_max'],'argmax':res['argmax'],
                 'n_cells':res['n_cells'],'n_hypotheses':res['n_hypotheses'],
                 'wall':round(time.time()-t0,1)})
    print(f"rep {r} grid_max={res['grid_max']} {res['argmax']['cfg']} {res['argmax']['name']} "
          f"a={res['argmax']['a']} {res['argmax']['w']} incell_z={res['argmax']['in_cell_z']} "
          f"({time.time()-t0:.0f}s)", flush=True)
    json.dump({'tag':TAG,'seed':SEED,'rows':rows,'wall':round(time.time()-t00,1)},
              open(f'results/adm_null_shuffle_{TAG}.json','w'), indent=1)
print('DONE', round(time.time()-t00,1))
