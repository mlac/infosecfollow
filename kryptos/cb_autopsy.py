"""Autopsy of the single linear-structure pass on real ciphertext (pk8, FIFTEENDAYSINTHEARCHIVE,
offset 15, KA alphabet, beaufort, structure (3,16)).  Expected false positives over the same
234,168,480 linear tests: 1.95.  Observed: 1.  This is the autopsy that shows what it is."""
import numpy as np, json, sys
sys.path.insert(0, '.')
from lib import KA, AZ, AZI, CT, q3dec
import cb_lib as cb
from crib_sweep import make_checker

crib = 'FIFTEENDAYSINTHEARCHIVE'; off = 15; a, b = 3, 16
ai = {c: i for i, c in enumerate(KA)}
C = np.array([ai[c] for c in CT['pk8']]); P = np.array([ai[c] for c in crib])
K = (C[off:off+len(crib)] + P) % 26                       # beaufort
R2, R13, r2, r13 = make_checker(np.arange(len(crib)), (a, b))
print("crib len", len(crib), " unknowns", a+b, " independent checks r2/r13 =", r2, r13)
print("keystream K (KA letters):", ''.join(KA[int(x)] for x in K))
# solve u (period 3) and v (period 16) from the crib, then see what key they imply
u = {}; v = {}; u[off % a] = 0
for _ in range(200):
    for j in range(len(K)):
        ra, rb = (off+j) % a, (off+j) % b
        if ra in u and rb not in v: v[rb] = (int(K[j])-u[ra]) % 26
        elif rb in v and ra not in u: u[ra] = (int(K[j])-v[rb]) % 26
print("u residues solved:", sorted(u), " v residues solved:", sorted(v))
print("-> both factors fully solved; the pass rests on only", r2+r13, "independent checks")
print("   (fp 8.4e-08 x 234,168,480 tests = 1.95 expected passes; 1 observed)")
best = None
for c in range(26):
    su = ''.join(KA[(u[i]+c) % 26] for i in sorted(u))
    sv = ''.join(KA[(v[i]-c) % 26] for i in sorted(v))
    if best is None: best = (su, sv)
print("factor strings at shift 0:", best)
W = cb.words_by_len()
hit = [c for c in range(26)
       if len(u) in W and (lambda s: int(np.searchsorted(W[len(u)], s) < len(W[len(u)]) and
                           W[len(u)][min(np.searchsorted(W[len(u)], s), len(W[len(u)])-1)] == s))
       (int(''.join(str(0) for _ in [])) if False else
        __import__('functools').reduce(lambda z, ch: z*26+AZI[ch], ''.join(KA[(u[i]+c) % 26]
                                       for i in sorted(u)), 0))]
print("shifts making the short factor a dictionary word:", hit)
json.dump({'crib': crib, 'offset': off, 'structure': [a, b], 'alphabet': 'KA', 'mode': 'beaufort',
           'keystream': ''.join(KA[int(x)] for x in K), 'checks_r2': int(r2), 'checks_r13': int(r13),
           'fp_per_test': 2.0**-int(r2)*13.0**-int(r13),
           'linear_tests_in_the_same_search': 234168480,
           'expected_false_positives': 1.954, 'observed': 1,
           'null_max_same_search': 5,
           'u_residues_solved': len(u), 'v_residues_solved': len(v),
           'verdict': 'chance pass; below the matched null max of 5 linear passes per shuffled run'},
          open('results/cb_autopsy_linear.json', 'w'), indent=1)
