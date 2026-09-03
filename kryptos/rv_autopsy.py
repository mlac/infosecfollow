"""rv_autopsy.py -- does the claimed hit's residual read as anything?

If the primer is right, residual R[i] = (c[i] - k[i]) mod 26 is MIX(P), a MONOALPHABETIC image
of the (possibly transposed) plaintext.  Two checks:
  (1) transposition-invariant: sorted unigram profile chi2 vs English  (works even under a columnar)
  (2) monoalphabetic hill-climb on quadgrams (valid only if no transposition underneath)
Both are run identically on the REAL residual and on the residual of each matched-null search's
own argmax primer -- so the comparison is matched to the search.
"""
import sys, json, os
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
import numpy as np
from rv_kern import to_ct_idx, keystream_rows
from lib import KA, AZ, CT, PT, load_quadgrams, qscore, col_enc

QG = load_quadgrams()
ENG_FREQ = np.array([.08167,.01492,.02782,.04253,.12702,.02228,.02015,.06094,.06966,.00153,
                     .00772,.04025,.02406,.06749,.07507,.01929,.00095,.05987,.06327,.09056,
                     .02758,.00978,.02360,.00150,.01974,.00074])
ENG_SORTED = np.sort(ENG_FREQ)[::-1]

def residual(ctstr, primer, alpha=KA, sign=-1, rec='aca', mod=10):
    c = to_ct_idx(ctstr, alpha).astype(int)
    k = keystream_rows(np.array([primer], np.uint8), len(c), rec, mod)[0].astype(int)
    return (c + sign * k) % 26

def profile_chi2(R):
    cnt = np.bincount(R, minlength=26).astype(float) / len(R)
    p = np.sort(cnt)[::-1]
    return float((((p - ENG_SORTED) ** 2) / ENG_SORTED).sum())

def climb(R, restarts=8, seed=0):
    rng = np.random.default_rng(seed)
    n = len(R); best = -99.0; bestkey = None
    pairs = [(i, j) for i in range(26) for j in range(i + 1, 26)]
    for r in range(restarts):
        key = rng.permutation(26)
        cur = qscore(key[R], QG)
        improved = True
        while improved:
            improved = False
            for i, j in pairs:
                key[i], key[j] = key[j], key[i]
                s = qscore(key[R], QG)
                if s > cur: cur = s; improved = True
                else: key[i], key[j] = key[j], key[i]
        if cur > best: best = cur; bestkey = key.copy()
    return float(best), bestkey

CLAIM = [2, 5, 4, 6, 7, 5, 4]
rows = []
R = residual(CT['pk9'], CLAIM)
q, key = climb(R, seed=1)
rows.append(('REAL pk9 claimed primer', float(np.bincount(R, minlength=26).astype(float) @ np.zeros(26)) or 0, profile_chi2(R), q,
             ''.join(AZ[v] for v in key[R])))

nullfile = 'results/rv_gromark_null.json'
if os.path.exists(nullfile):
    nd = json.load(open(nullfile))['draws']
    base = np.array(list(CT['pk9']))
    for d in nd:
        rng = np.random.default_rng(d['seed'])
        sh = ''.join(base[rng.permutation(len(base))])
        Rn = residual(sh, d['best_primer'])
        qn, kn = climb(Rn, seed=d['seed'])
        rows.append(('null seed %d' % d['seed'], d['best'], profile_chi2(Rn), qn, ''.join(AZ[v] for v in kn[Rn])[:60]))

# genuine monoalphabetic English references at n=144
rng = np.random.default_rng(31337)
for i in range(6):
    src = ''.join(ch for ch in PT[['pk1','pk2','pk3','pk4','pk5','pk6'][i]] if ch.isalpha())[:144]
    mix = rng.permutation(26)
    Re = mix[to_ct_idx(src, AZ).astype(int)]
    qe, ke = climb(Re, seed=100 + i)
    rows.append(('ENGLISH ref %d' % i, 0.0, profile_chi2(Re), qe, ''.join(AZ[v] for v in ke[Re])[:60]))

print('%-24s %-9s %-9s %-9s %s' % ('case', 'search', 'profchi2', 'climb_q', 'climbed text'))
for r in rows:
    print('%-24s %-9.6f %-9.4f %-9.4f %s' % (r[0], r[1], r[2], r[3], r[4][:60]))
json.dump({'rows': [[r[0], r[1], r[2], r[3], r[4]] for r in rows]},
          open('results/rv_gromark_autopsy.json', 'w'), indent=1)
print('\nREAL residual full climbed text:\n', rows[0][4])
