import json,os
rows=[('PK1 positive-control grid, beam 20k (two grids, 12 + 10)',22),
      ('PK1 positive-control grid, beam 100k',6),
      ('dual-beam timing/validation on 504 synthetic',1),
      ('exploratory hard-constraint periodic runs (superseded by periodic_beam2)',8)]
def J(f): return json.load(open('results/'+f))
rows.append(('dual beam: 504 synthetics + real PK8/PK9/PK10, KA, beam 100k',len(J('wb_dual_real.json'))))
rows.append(('dual beam: real PK10, A-Z alphabet, beam 100k',len(J('wb_dual_az.json'))))
rows.append(('dual beam: power-boundary synthetics + PK10 at kmin 5,6,7',len(J('wb_dual_power.json'))))
rows.append(('dual MATCHED NULL, PK10 shuffles, kmin>=10',len(J('wb_dual_null_k10.json'))))
rows.append(('dual MATCHED NULL, PK10 shuffles, kmin>=8',len(J('wb_dual_null_k8.json'))))
d=J('wb_dual_null_p89.json'); rows.append(('dual LENGTH-MATCHED NULL, PK8+PK9 shuffles x 3 modes',sum(len(v['rows'])*3 for v in d.values())))
rows.append(('periodic beam: positive controls + real PK8/PK9/PK10 over 16 periods x 3 modes',len(J('wb_periodic_real.json'))))
n=0
for f in ('wb_periodic_null_0.json','wb_periodic_null_10.json'): n+=len(J(f))*16
rows.append(('periodic MATCHED NULL, 20 PK10 shuffles x 16 periods',n))
d=J('wb_periodic_null_p89.json'); rows.append(('periodic MATCHED NULL at L=63, PK8+PK9 shuffles x 2 modes',sum(len(v['rows'])*2 for v in d.values())))
tot=0
for a,b in rows: print(f'{b:6d}  {a}'); tot+=b
print(f'{tot:6d}  TOTAL beam executions (every one at beam 100,000 except the two PK1 grids at 20k)')
