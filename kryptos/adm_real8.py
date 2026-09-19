"""Verify with my own engine that 0.06313 really is the maximum of the REAL pk9 M-A search
over all 8 alphabet/mode configs (the claim asserts this from its own log; I check it)."""
import sys, json, time; sys.path.insert(0,'.')
import numpy as np, adm_engine as E
from lib import CT
eng=E.Engine(); rows=[]; t00=time.time()
for cfg in E.CONFIGS:
    t0=time.time(); r=eng.run(CT['pk9'], configs=[cfg])
    rows.append({'cfg':f'{cfg[0]}/{cfg[1]}/{cfg[2]}','grid_max':r['grid_max'],
                 'argmax':r['argmax'],'wall':round(time.time()-t0,1)})
    print(rows[-1]['cfg'], r['grid_max'], r['argmax']['name'], r['argmax']['a'],
          r['argmax']['w'], f"({time.time()-t0:.0f}s)", flush=True)
    json.dump({'per_config':rows,
      'overall_max':max(x['grid_max'] for x in rows),
      'claim_asserts':0.06313,'wall':round(time.time()-t00,1)},
      open('results/adm_real8.json','w'), indent=1)
print('OVERALL MAX', max(x['grid_max'] for x in rows))
