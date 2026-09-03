"""DERIVED NULL + POSITIVE CONTROL, rebuilt from scratch.
Derived null = REAL Kryptos-family ciphertexts truncated to n=144 whose true keys lie
OUTSIDE the single-word manufactured family. These keep the positional letter clustering
that a shuffle destroys. PK6 is EXCLUDED as contaminated (its key PORTAL has period 6 and
is exactly the 'plain' construction). PK2 is EXCLUDED (pure transposition -> English IoC).
Positive control = PK1 truncated to n=144 (true key PROVENANCE, period 10 = 'plain').
"""
import sys, json, time; sys.path.insert(0,'.')
import numpy as np
import adm_engine as E
from lib import CT, ioc

eng=E.Engine()
def IOC(s):
    import numpy as np
    c=np.bincount(E.to_idx(s,E.AZ).astype(np.int64),minlength=26).astype(float)
    L=len(s); return round(float((c*(c-1)).sum()/(L*(L-1))),5)

CASES=[
 ('POSCTRL_pk1_trunc144', CT['pk1'][:144], 'true key PROVENANCE period 10 = plain construction'),
 ('DERIVED_pk3_trunc144', CT['pk3'][:144], 'true key = q3enc(PENTIMENTOx4,ORDINATE) period 40, OUTSIDE M-A'),
 ('DERIVED_pk3_tail144',  CT['pk3'][-144:],'same, tail window'),
 ('DERIVED_pk4_trunc144', CT['pk4'][:144], 'columnar W8 + period-45 two-word product, OUTSIDE M-A'),
 ('DERIVED_pk5_trunc144', CT['pk5'][:144], 'columnar + running key = PK4 plaintext, OUTSIDE M-A'),
 ('DERIVED_pk7_trunc144', CT['pk7'][:144], 'Hill 3x3 + period-2 additive, OUTSIDE M-A'),
 ('DERIVED_pk10_head144', CT['pk10'][:144],'unsolved sibling, head window'),
 ('DERIVED_pk10_tail144', CT['pk10'][-144:],'unsolved sibling, tail window'),
 ('DERIVED_pk8_head144',  CT['pk8'][:144], 'unsolved sibling pk8, head window'),
]
rows=[]; t00=time.time()
for name,ct,note in CASES:
    if len(ct)!=144:
        print('SKIP',name,len(ct)); continue
    t0=time.time(); res=eng.run(ct)
    rows.append({'label':name,'note':note,'n':len(ct),'ct_ioc':IOC(ct),
                 'grid_max':res['grid_max'],'argmax':res['argmax'],
                 'wall':round(time.time()-t0,1)})
    print(f"{name} ct_ioc={IOC(ct)} grid_max={res['grid_max']} "
          f"{res['argmax']['cfg']} {res['argmax']['name']} a={res['argmax']['a']} "
          f"{res['argmax']['w']} ({time.time()-t0:.0f}s)", flush=True)
    json.dump({'rows':rows,'wall':round(time.time()-t00,1)},
              open('results/adm_null_derived.json','w'), indent=1)
print('DONE', round(time.time()-t00,1))
