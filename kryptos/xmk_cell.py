"""xmk_cell: the properly matched null for the IN-CELL z the pipeline reports.

The claim's headline row carries z=+8.1.  That z is (max - mean)/sd taken over the ~30k dictionary
words INSIDE ONE CELL (construction revtrunc14, a=9, config KA/AZ/sub).  It answers 'is METALHEAD
unusual among 9-letter words for this ciphertext', which is not the question.  The matched null is
the distribution of that same cell's MAXIMUM over ciphertexts drawn from the null ensemble.
Same code path, same word list, same construction, same config."""
import sys, json, time; sys.path.insert(0,'.')
import numpy as np
from lib import KA, AZ, CT, PT, q3enc, ioc
import mk_lib as M
import xmk_core as X
ALPH={'KA':KA,'AZ':AZ}
byl=X.byl

CELLS=[('pk9','KA','AZ','sub',9,'revtrunc14',0.06313,8.1),
       ('pk9','AZ','AZ','sub',10,'trunc14',0.06167,9.46),
       ('pk9','AZ','KA','add',7,'plain',0.05876,7.77)]
NSH=150
rng=np.random.default_rng(4242)
pool=''.join(PT[k] for k in ('pk1','pk2','pk3','pk4','pk5','pk6','pk7'))
out={'n_shuffles':NSH,'cells':[]}
t00=time.time()
for (tgt,ta,ka,md,a,name,claim_ioc,claim_z) in CELLS:
    Wv=X.WM[ka][a]
    n=len(CT[tgt])
    cm=off=None
    for (nm,which,c_,o_) in X.constructions(a,n,ka):
        if nm==name: cm,off,whichW=c_,o_,which; break
    Wuse=X.WM[ka][a] if whichW=='W' else X.WCAT[ka][a]
    def cellmax(ct):
        C=M.to_idx(ct,ALPH[ta])
        sc=M.score_parts(C,Wuse,[(np.arange(len(C)),cm)],md,off)
        return float(sc.max()),float(sc.mean()),float(sc.std())
    rmax,rmu,rsd=cellmax(CT[tgt])
    sh=[cellmax(M.shuffled(CT[tgt],rng))[0] for _ in range(NSH)]
    # synthetic outside-family periodic ciphers, same length
    syn=[]
    for _ in range(NSH//3):
        L=int(rng.choice([7,9,11,13,17,23])); s=int(rng.integers(0,len(pool)-n))
        key=''.join(KA[int(v)] for v in rng.integers(0,26,L))
        syn.append(cellmax(q3enc(pool[s:s+n],[key]))[0])
    sh=np.array(sh); syn=np.array(syn)
    rec={'target':tgt,'cfg':f'{ta}/{ka}/{md}','a':a,'construction':name,
     'claimed_ioc':claim_ioc,'claimed_in_cell_z':claim_z,
     'recomputed_real_cell_max':round(rmax,5),
     'in_cell_mean':round(rmu,5),'in_cell_sd':round(rsd,5),
     'in_cell_z_recomputed':round((rmax-rmu)/rsd,2),
     'SHUFFLE_null_cellmax':{'n':int(len(sh)),'mean':round(float(sh.mean()),5),
        'sd':round(float(sh.std(ddof=1)),5),'max':round(float(sh.max()),5),
        'p95':round(float(np.percentile(sh,95)),5),
        'z_of_real':round(float((rmax-sh.mean())/sh.std(ddof=1)),2),
        'exact_p':round(float((1+(sh>=rmax).sum())/(1+len(sh))),4)},
     'SYNTH_outside_family_null_cellmax':{'n':int(len(syn)),'mean':round(float(syn.mean()),5),
        'sd':round(float(syn.std(ddof=1)),5),'max':round(float(syn.max()),5),
        'p95':round(float(np.percentile(syn,95)),5),
        'z_of_real':round(float((rmax-syn.mean())/syn.std(ddof=1)),2),
        'exact_p':round(float((1+(syn>=rmax).sum())/(1+len(syn))),4)}}
    out['cells'].append(rec); print(json.dumps(rec,indent=1),flush=True)
out['wall']=round(time.time()-t00,1)
json.dump(out,open('results/xmk_cell.json','w'),indent=1)
print('WALL',out['wall'])
