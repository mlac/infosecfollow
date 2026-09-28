"""Multiple-testing analysis on the SINGLE config that contains the claimed hit (KA/AZ/sub).
This sub-search is BIASED IN THE CLAIM'S FAVOUR: the real 0.06313 was the maximum over
EIGHT such grids, while each null replicate here is the maximum over ONE. If the claim
already fails against this null it fails a fortiori against the properly matched one.
"""
import sys, json, time; sys.path.insert(0,'.')
import numpy as np
import adm_engine as E
from lib import CT

CFG=[('KA','AZ','sub')]
eng=E.Engine()
t00=time.time()
out={}

# --- the real grid, keeping every cell maximum -> the order statistics of the search
r=eng.run(CT['pk9'], configs=CFG, keep_cells=True)
cells=sorted(r['cells'], key=lambda c:-c[0])
out['real_pk9_one_config']={
 'grid_max':r['grid_max'],'argmax':r['argmax'],
 'n_cells':r['n_cells'],'n_word_hypotheses_this_config':r['n_hypotheses'],
 'top20_cell_maxima':[{'ioc':c[0],'cfg':c[1],'name':c[2],'a':c[3]} for c in cells[:20]],
 'cell_max_mean':round(float(np.mean([c[0] for c in cells])),5),
 'cell_max_sd':round(float(np.std([c[0] for c in cells])),5)}
cm=np.array([c[0] for c in cells])
out['real_pk9_one_config']['cell_max_quantiles']={
 q:round(float(np.quantile(cm,q)),5) for q in (0.5,0.9,0.99,0.999,1.0)}
print('real one-config grid max', r['grid_max'], flush=True)
print('top cells:', [(c[0],c[2],c[3]) for c in cells[:8]], flush=True)
json.dump(out, open('results/adm_multipletesting.json','w'), indent=1)

# --- shuffle null on the identical one-config search
rng=np.random.default_rng(777001)
nulls=[]
for i in range(40):
    ct=E.shuffled(CT['pk9'],rng)
    t0=time.time()
    rr=eng.run(ct, configs=CFG)
    nulls.append({'rep':i,'grid_max':rr['grid_max'],'argmax':rr['argmax']})
    v=np.array([x['grid_max'] for x in nulls])
    out['shuffle_null_one_config']={
      'n_replicates':len(v),'mean':round(float(v.mean()),5),'sd':round(float(v.std(ddof=1)),5),
      'min':round(float(v.min()),5),'p95':round(float(np.quantile(v,0.95)),5),
      'max':round(float(v.max()),5),
      'n_ge_real':int((v>=r['grid_max']).sum()),
      'exact_permutation_p':round((int((v>=r['grid_max']).sum())+1)/(len(v)+1),4),
      'z_of_real':round((r['grid_max']-float(v.mean()))/float(v.std(ddof=1)),2),
      'rows':nulls}
    json.dump(out, open('results/adm_multipletesting.json','w'), indent=1)
    print(f"null {i} {rr['grid_max']} {rr['argmax']['name']} a={rr['argmax']['a']} "
          f"{rr['argmax']['w']} ({time.time()-t0:.0f}s) running_max={v.max():.5f}", flush=True)
print('DONE',round(time.time()-t00,1))
