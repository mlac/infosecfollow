"""Positive control for the cross-target key-free crib join: plant a shared keystream."""
import numpy as np, sys, json
sys.path.insert(0, '.')
from lib import KA, CT
from cb_corpus import corpus
CORP = [s for s, r, k in corpus(99999, 99999, 99999) if len(s) >= 12]
A, B = CORP[0], CORP[7]
ai = {c: i for i, c in enumerate(KA)}
rng = np.random.default_rng(1)
K = rng.integers(0, 26, 12)
X = list(CT['pk8']); Y = list(CT['pk9'])
for i in range(12):
    X[3+i] = KA[(ai[A[i]] + int(K[i])) % 26]
    Y[5+i] = KA[(ai[B[i]] + int(K[i])) % 26]
X = ''.join(X); Y = ''.join(Y)
sys.argv = ['x', 'pc']
src = open('cb_pair.py').read().split("t0 = time.time(); OUT = {}")[0]
g = {'__name__': 'pc'}
exec(src, g)
OUT = {}
g['run']({'apk8': X, 'bpk9': Y}, 'planted', OUT)
h = OUT['planted']['hits']
found = any(A in x['A'] and B in x['B'] and x['offX'] == 3 and x['offY'] == 5 for x in h) or \
        any(B in x['A'] and A in x['B'] for x in h)
print("planted A =", A, "\nplanted B =", B)
print("hits:", h[:3])
print("RECOVERED:", found)
json.dump({'planted_A': A, 'planted_B': B, 'n_hits': len(h), 'recovered': bool(found),
           'hits': h[:5]}, open('results/cb_pair_pc.json', 'w'), indent=1, default=str)
