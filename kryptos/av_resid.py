"""Matched-null residual test.  Under the claimed model a correct primer leaves MIX(P):
a monoalphabetic image of the (possibly transposed) plaintext.  Compare the claimed hit's
residual against the residuals of the BEST-OF-SEARCH primers from the identical searches on
shuffled copies -- and against genuine monoalphabetic images of English of the same length."""
import sys, json, random
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
import numpy as np
from av_gk_lib import cidx, ks, ioc1
from lib import KA, AZ, CT, PT
from av_autopsy import qscore, climb, profile_fit, residual

d = json.load(open('results/av_gromark_null.json'))
rows = []
r = residual(CT['pk9'], KA, -1, d['real']['best_primer'])
q, _ = climb(r, seed=1)
rows.append(('REAL  ', d['real']['best'], ioc1(r), profile_fit(r), q))
for i, nl in enumerate(d['nulls']):
    rr = random.Random(nl['seed']); l = list(CT['pk9']); rr.shuffle(l); sh = ''.join(l)
    res = residual(sh, KA, -1, nl['best_primer'])
    q, _ = climb(res, seed=100 + i)
    rows.append(('null%02d' % i, nl['best'], ioc1(res), profile_fit(res), q))

print('%-7s %9s %9s %11s %9s' % ('cell', 'best_ioc', 'res_ioc', 'prof_chi2', 'climb_q'))
for t, b, io, pf, q in rows:
    print('%-7s %9.6f %9.6f %11.4f %9.4f' % (t, b, io, pf, q))
nq = np.array([x[4] for x in rows[1:]]); npf = np.array([x[3] for x in rows[1:]])
print()
print('null climb_q   : mean %.4f sd %.4f  min %.4f max %.4f' % (nq.mean(), nq.std(ddof=1), nq.min(), nq.max()))
print('real climb_q   : %.4f   z = %+.2f' % (rows[0][4], (rows[0][4]-nq.mean())/nq.std(ddof=1)))
print('null prof_chi2 : mean %.4f sd %.4f  min %.4f max %.4f' % (npf.mean(), npf.std(ddof=1), npf.min(), npf.max()))
print('real prof_chi2 : %.4f   z = %+.2f (LOWER is more English)' % (rows[0][3], (rows[0][3]-npf.mean())/npf.std(ddof=1)))
print('reference: genuine monoalphabetic image of English n=144 -> climb_q -4.24..-4.88, prof_chi2 0.058')
json.dump({'rows': [list(x) for x in rows]}, open('results/av_gromark_resid.json', 'w'), indent=1)
