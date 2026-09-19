"""xmk_null: rebuild the matched null for the M-A single-word manufactured-key search FROM SCRATCH.

The statistic under test is exactly the one the claim reports: the maximum decrypt-IoC over one
complete M-A search of a length-144 ciphertext (696 constructions x 8 alphabet/mode configs
x the whole dictionary).  One replicate = one ciphertext = one such maximum.

Three null ensembles, all run through xmk_core.search_one_ct (identical code to the real run):
  S  shuffle   : uniform letter permutations of pk9 (the claim's own null), 10 replicates
  D  derived   : 144-letter windows of REAL sibling ciphertexts whose true keys are known to lie
                 OUTSIDE the single-word family (pk3 two-word product, pk4 product+columnar,
                 pk5 running key, pk7 Hill).  pk1/pk6 excluded as CONTAMINATED (their true keys
                 PROVENANCE / PORTAL *are* plain single dictionary words, i.e. inside the family);
                 pk2 excluded (pure transposition, plaintext-IoC ciphertext).
  N  synthetic : real sibling plaintext, 144 letters, encrypted with a RANDOM period-L key
                 (L in {7,9,11,13,17,23}) on KA -- a genuine periodic polyalphabetic cipher whose
                 key is not a dictionary word and not any member of the manufactured family.
"""
import sys, json, time; sys.path.insert(0,'.')
import numpy as np
sys.path.insert(0,'/home/user/infosecfollow/kryptos')
from lib import KA, AZ, CT, PT, q3enc, ioc
import mk_lib as M
import xmk_core as X

N=144
rng=np.random.default_rng(20260903)
recs=[]
t00=time.time()

def emit(kind,label,ct):
    t0=time.time()
    rm,cells,best,_=X.search_one_ct(ct)
    r={'kind':kind,'label':label,'n':len(ct),'ct_ioc':round(float(ioc(M.to_idx(ct,AZ))),5),
       'run_max_over_8_configs':round(float(max(rm)),5),
       'per_config_maxima':[round(float(v),5) for v in rm],
       'cells_per_config':cells,'best':best,'sec':round(time.time()-t0,1)}
    recs.append(r)
    print(json.dumps(r),flush=True)
    json.dump({'replicates':recs,'wall':round(time.time()-t00,1)},
              open('results/xmk_null.json','w'),indent=1)

# --- the REAL observation, recomputed here with the identical code path
emit('REAL','pk9',CT['pk9'])

# --- S: shuffle null (the claim's own construction), 10 replicates
for i in range(10):
    emit('S',f'pk9_shuffle{i}',M.shuffled(CT['pk9'],rng))

# --- D: derived null from real sibling ciphertexts, keys known outside the family
for tag in ('pk3','pk4','pk5','pk7'):
    c=CT[tag]
    for off in (0,len(c)-N):
        emit('D',f'{tag}[{off}:{off+N}]',c[off:off+N])

# --- N: synthetic outside-family periodic ciphers on real sibling plaintext
pool=''.join(PT[k] for k in ('pk1','pk2','pk3','pk4','pk5','pk6','pk7'))
for i in range(10):
    L=int(rng.choice([7,9,11,13,17,23]))
    s=int(rng.integers(0,len(pool)-N))
    key=''.join(KA[int(v)] for v in rng.integers(0,26,L))
    emit('N',f'synth_L{L}_{i}',q3enc(pool[s:s+N],[key]))

print('DONE wall',round(time.time()-t00,1))
