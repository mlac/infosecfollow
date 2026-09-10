"""xmk_pc: independent positive control -- what does a TRUE member of the M-A family look like
under the identical search?  PK1 has key PROVENANCE (a plain dictionary word, period 10, Q3 on KA),
i.e. it IS an M-A 'plain' instance.  Run the identical search on PK1 full (n=192) and on PK1
truncated to n=144 (pk9's length)."""
import sys, json, time; sys.path.insert(0,'.')
import numpy as np
from lib import KA, AZ, CT, PT, ioc, qscore, ka_to_az
import mk_lib as M
import xmk_core as X
out={}
for label, ct in (('pk1_full_n192',CT['pk1']),('pk1_trunc_n144',CT['pk1'][:144])):
    t0=time.time()
    rm,cells,best,allc=X.search_one_ct(ct,want_cells=True)
    # rank of the TRUE key in its own cell
    C=M.to_idx(ct,KA); n=len(C)
    cm=(np.arange(n)%10)
    sc=M.score_parts(C,X.WM['KA'][10],[(np.arange(n),cm)],'sub',None)
    words=X.byl[10]; idx=words.index('PROVENANCE')
    rank=int((sc>sc[idx]).sum())+1
    S=np.array([KA.index(c) for c in 'PROVENANCE'])[cm]
    R=(C-S)%26; pt=''.join(KA[int(v)] for v in R)
    allc=np.array(allc)
    out[label]={'search_run_max_over_8_configs':round(float(max(rm)),5),
      'global_argmax_record':best,
      'true_key_PROVENANCE_ioc':round(float(sc[idx]),5),
      'true_key_rank_in_its_cell':rank,'cell_size':int(len(sc)),
      'true_key_is_global_argmax':bool(best['w']=='PROVENANCE' and best['name']=='plain'),
      'decrypt_quadgram_per_letter':round(qscore(ka_to_az(pt)),3),
      'decrypt_head':pt[:60],
      'cell_max_distribution_over_5568_cells':{
         'mean':round(float(allc.mean()),5),'p50':round(float(np.percentile(allc,50)),5),
         'p99':round(float(np.percentile(allc,99)),5),'max':round(float(allc.max()),5)},
      'sec':round(time.time()-t0,1)}
    print(json.dumps(out[label],indent=1),flush=True)
json.dump(out,open('results/xmk_positive_control.json','w'),indent=1)
