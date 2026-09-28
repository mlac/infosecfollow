"""rv_null.py -- rebuild the MATCHED null for the claimed cell from scratch.

Matched means: the IDENTICAL search (full 10^7 primer enumeration, rec=aca, L=7, mod 10,
KA text alphabet, sign -1, shift-IoC statistic, n=144) run against a letter-shuffled copy of
pk9 (same length, same letter multiset, position order destroyed).  The null statistic is the
BEST-OF-SEARCH, i.e. the same max-over-10^7 that produced the real number.
Seeds are the verifier's own (900000+), independent of the claim's 1001/2002 and of the
earlier av_null.py's 770000-770019.
"""
import sys, os, json, time
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
import numpy as np
from rv_kern import to_ct_idx, enumerate_full
from lib import KA, CT

NDRAW = int(os.environ.get('NDRAW', '40'))
OUT = '/home/user/infosecfollow/kryptos/results/rv_gromark_null.json'

base = np.array(list(CT['pk9']))
rows = []
t0 = time.time()
for d in range(NDRAW):
    seed = 900000 + d
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(base))
    sh = ''.join(base[perm])
    assert sorted(sh) == sorted(CT['pk9']) and len(sh) == len(CT['pk9'])
    c = to_ct_idx(sh, KA)
    b, p, m, sd, cnt = enumerate_full(c, 7, 10, 'aca', -1, chunk=200000)
    rows.append({'seed': seed, 'best': float(b[0]), 'best_primer': [int(x) for x in p[0]],
                 'top8': [float(x) for x in b], 'per_primer_mean': float(m),
                 'per_primer_sd': float(sd), 'count': int(cnt)})
    bo = np.array([r['best'] for r in rows])
    print('draw %d seed %d best %.6f | running mean %.6f sd %.6f max %.6f | %.0f s'
          % (d, seed, b[0], bo.mean(), bo.std(ddof=1) if len(bo) > 1 else 0.0, bo.max(),
             time.time() - t0), flush=True)
    json.dump({'cell': 'pk9.KA.sign-1.aca.L7.mod10', 'n': 144, 'primers': 10**7,
               'draws': rows}, open(OUT, 'w'), indent=1)
print('DONE %.0f s' % (time.time() - t0), flush=True)
