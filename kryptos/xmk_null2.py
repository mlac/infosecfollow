"""xmk_null2: lean, well-powered matched null for the M-A headline.

Statistic: the maximum decrypt-IoC over ONE complete 696-cell M-A grid, run in the single
alphabet/mode config that produced the headline (KA/AZ/sub).  The real observation, 0.06313,
was the max over EIGHT such configs, so comparing it to a null of one-config maxima is
CONSERVATIVE IN THE CLAIM'S FAVOUR -- if it still fails to separate, it fails decisively.

Ensembles (all through the identical xmk_core code path):
  S  40 uniform letter shuffles of pk9          (the claim's own null; preserves the multiset,
                                                 hence pk9's exact ciphertext IoC 0.04448)
  N  20 synthetic outside-family periodic ciphers: real sibling plaintext, n=144, encrypted with
       a RANDOM period-L key on KA (L in 7..23) -- a real periodic polyalphabetic cipher whose
       key is NOT in the manufactured family.  Preserves positional letter clustering, which a
       shuffle destroys.
  D  8 windows of REAL sibling ciphertexts with keys known to be outside the family
       (pk3 two-word product, pk4 product+columnar, pk5 running key, pk7 Hill).
  POSCTL  PK1 (true key PROVENANCE, a plain single dictionary word = an M-A 'plain' instance)
       full and truncated to n=144, in its own config KA/KA/sub.
"""
import sys, json, time; sys.path.insert(0, '.')
import numpy as np
from lib import KA, AZ, CT, PT, q3enc, ioc
import mk_lib as M
import xmk_core as X

ALPH = {'KA': KA, 'AZ': AZ}
CFG = ('KA', 'AZ', 'sub')
rng = np.random.default_rng(31337)
recs = []
t00 = time.time()


def emit(kind, label, ct, cfg=CFG):
    t0 = time.time()
    rm, cells, best, _ = X.search_one_ct(ct, configs=[cfg])
    r = {'kind': kind, 'label': label, 'cfg': '/'.join(cfg), 'n': len(ct),
         'ct_ioc': round(float(ioc(M.to_idx(ct, AZ))), 5),
         'grid_max': round(float(rm[0]), 5), 'cells': cells, 'argmax': best,
         'sec': round(time.time() - t0, 1)}
    recs.append(r)
    print(json.dumps(r), flush=True)
    json.dump({'design': 'one 696-cell M-A grid per replicate, config KA/AZ/sub',
               'replicates': recs, 'wall': round(time.time() - t00, 1)},
              open('results/xmk_null2.json', 'w'), indent=1)


emit('REAL', 'pk9', CT['pk9'])
emit('POSCTL', 'pk1_full_n192', CT['pk1'], ('KA', 'KA', 'sub'))
emit('POSCTL', 'pk1_trunc_n144', CT['pk1'][:144], ('KA', 'KA', 'sub'))
pool = ''.join(PT[k] for k in ('pk1', 'pk2', 'pk3', 'pk4', 'pk5', 'pk6', 'pk7'))
for i in range(20):
    L = int(rng.choice([7, 9, 10, 11, 13, 14, 17, 23]))
    s = int(rng.integers(0, len(pool) - 144))
    key = ''.join(KA[int(v)] for v in rng.integers(0, 26, L))
    emit('N', f'synth_L{L}_{i}', q3enc(pool[s:s + 144], [key]))
for tag in ('pk3', 'pk4', 'pk5', 'pk7'):
    c = CT[tag]
    for off in (0, len(c) - 144):
        emit('D', f'{tag}[{off}:{off + 144}]', c[off:off + 144])
for i in range(40):
    emit('S', f'pk9_shuffle{i}', M.shuffled(CT['pk9'], rng))
print('DONE wall', round(time.time() - t00, 1))
