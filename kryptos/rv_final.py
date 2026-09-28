"""rv_final.py -- assemble the verdict on the claimed Gromark hit."""
import sys, json, math
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
import numpy as np

nd = json.load(open('results/rv_gromark_null.json'))['draws']
b = np.array([d['best'] for d in nd])
REAL = 0.06371406371406371
m, sd = b.mean(), b.std(ddof=1)
z = (REAL - m) / sd
# Gumbel fit by method of moments (best-of-search maxima)
scale = sd * math.sqrt(6) / math.pi
loc = m - 0.5772156649 * scale
p1 = 1.0 - math.exp(-math.exp(-(REAL - loc) / scale))
print('MATCHED NULL, rebuilt from scratch (identical search: full 10^7 primer enumeration,')
print('rec=aca L=7 mod10, KA alphabet, sign -1, shift-IoC, n=144, letter-shuffled pk9)')
print('  draws=%d seeds 900000-%d' % (len(b), 900000 + len(b) - 1))
print('  best-of-search: mean %.6f  sd %.6f  min %.6f  max %.6f' % (m, sd, b.min(), b.max()))
print('  real best = %.6f   n_null >= real = %d' % (REAL, int((b >= REAL).sum())))
print('  RECOMPUTED z (matched) = %+.2f      [claim reported z = +11.98]' % z)
print('  Gumbel(loc=%.6f, scale=%.6f) -> p(one cell) = %.4f' % (loc, scale, p1))
for K, lbl in [(32, 'comparable-scale cells (n=144, shift-IoC, >=1e7 primers)'),
               (2032, 'all real cells in the family')]:
    fw = 1 - (1 - p1) ** K
    print('  familywise p over %4d %s = %.3f  -> expected exceedances %.1f' % (K, lbl, fw, K * p1))
# expected maximum of K independent Gumbel draws
for K in (32, 2032):
    em = loc + scale * (math.log(K) + 0.5772156649)
    print('  expected MAX of %d such searches = %.6f   (observed max over real cells = %.6f)' % (K, em, REAL))
json.dump({'null_bos_mean': float(m), 'null_bos_sd': float(sd), 'null_bos_max': float(b.max()),
           'null_bos_min': float(b.min()), 'draws': int(len(b)), 'real': REAL,
           'z_matched': float(z), 'gumbel_loc': loc, 'gumbel_scale': scale, 'p_one_cell': p1,
           'n_null_ge_real': int((b >= REAL).sum())}, open('results/rv_gromark_final.json', 'w'), indent=1)
