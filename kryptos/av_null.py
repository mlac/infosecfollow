"""Rebuild the matched best-of-search null for the claimed top Gromark hit, from scratch.

Claimed hit: cell pk9.real.KA.m, L=7, mod 10, rec=aca, text alphabet KA, sign -1,
             primer [2,5,4,6,7,5,4], IoC 0.063714, 10^7 primers enumerated.

The matched null must be: the IDENTICAL enumeration (all 10^7 primers, same recurrence,
same alphabet, same sign, same statistic, same n) run on a letter-shuffled copy of pk9
(same length, same letter multiset).  The comparison statistic is the BEST-OF-SEARCH
maximum, not the per-primer mean/sd.
"""
import sys, time, json, random
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
import numpy as np
from av_gk_lib import cidx, enum_best
from lib import CT, KA

NNULL = int(sys.argv[1]) if len(sys.argv) > 1 else 20
CH = 200000
out = {'cell': 'pk9.KA.m.aca.L7.mod10', 'n': 144, 'primers': 10**7, 'nulls': []}

t0 = time.time()
c = cidx(CT['pk9'], KA)
b, p, m, s = enum_best(c, -1, 'aca', 10, 7, chunk=CH)
out['real'] = {'best': b, 'best_primer': p, 'per_primer_mean': m, 'per_primer_sd': s,
               'sec': round(time.time() - t0, 1)}
print('REAL best=%.6f primer=%s permean=%.6f persd=%.6f  %.0fs' % (b, p, m, s, time.time()-t0), flush=True)

for i in range(NNULL):
    seed = 770000 + i            # my own seeds, independent of the claim's 1001/2002
    r = random.Random(seed)
    l = list(CT['pk9']); r.shuffle(l); sh = ''.join(l)
    assert sorted(sh) == sorted(CT['pk9'])
    t1 = time.time()
    cb, cp, cm, cs = enum_best(cidx(sh, KA), -1, 'aca', 10, 7, chunk=CH)
    out['nulls'].append({'seed': seed, 'best': cb, 'best_primer': cp,
                         'per_primer_mean': cm, 'per_primer_sd': cs})
    print('NULL %2d seed=%d best=%.6f primer=%s permean=%.6f persd=%.6f  %.0fs'
          % (i, seed, cb, cp, cm, cs, time.time()-t1), flush=True)
    json.dump(out, open('results/av_gromark_null.json', 'w'), indent=1)

bs = np.array([x['best'] for x in out['nulls']])
mu, sd = float(bs.mean()), float(bs.std(ddof=1))
out['null_bos_mean'] = mu; out['null_bos_sd'] = sd
out['null_bos_max'] = float(bs.max()); out['null_bos_min'] = float(bs.min())
out['z_matched'] = (out['real']['best'] - mu) / sd
out['n_null_ge_real'] = int((bs >= out['real']['best']).sum())
json.dump(out, open('results/av_gromark_null.json', 'w'), indent=1)
print('\n=== MATCHED BEST-OF-SEARCH NULL (%d shuffles, 10^7 primers each) ===' % NNULL, flush=True)
print('null best-of-search: mean=%.6f sd=%.6f min=%.6f max=%.6f' % (mu, sd, bs.min(), bs.max()), flush=True)
print('real best = %.6f   z_matched = %+.2f   #null>=real = %d/%d'
      % (out['real']['best'], out['z_matched'], out['n_null_ge_real'], NNULL), flush=True)
print('DONE %.0fs' % (time.time()-t0), flush=True)
