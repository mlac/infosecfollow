import json,glob,os
tot=0; rows=[]
def n(f,label):
    global tot
    if not os.path.exists(f): return
    k=len(json.load(open(f))); rows.append((label,k)); tot+=k
n('results/wb_pc1_beam20000.json','PK1 positive-control grid, beam 20k')
n('results/wb_pc1_beam100000.json','PK1 positive-control grid, beam 100k')
n('results/wb_dual_real.json','dual beam, synthetics + real PK8/9/10 (KA), beam 100k')
n('results/wb_dual_az.json','dual beam, real PK10 (AZ), beam 100k')
n('results/wb_dual_null_k10.json','dual matched null kmin=10, beam 100k')
n('results/wb_dual_null_k8.json','dual matched null kmin=8, beam 100k')
n('results/wb_periodic_real.json','periodic beam, PC + real PK8/9/10, beam 100k')
for f in sorted(glob.glob('results/wb_periodic_null_*.json')):
    k=len(json.load(open(f)))*16; rows.append((f'periodic matched null ({os.path.basename(f)}), 16 periods each',k)); tot+=k
rows.append(('exploratory hard-constraint periodic runs (wb_ptest/2/3, superseded)',8))
tot+=8
rows.append(('dual-beam timing/validation run on synthetic (wb_time)',1)); tot+=1
for a,b in rows: print(f'{b:6d}  {a}')
print(f'{tot:6d}  TOTAL beam executions')
