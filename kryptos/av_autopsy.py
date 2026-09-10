"""Autopsy of the claimed top Gromark hit: pk9 / L=7 / mod10 / aca / KA / sign-1 / primer 2546754.
Under the model C = MIX(P)+k, peeling the true k must leave MIX(P): a monoalphabetic image of
the (possibly transposed) plaintext.  Two checks, one transposition-sensitive, one invariant."""
import sys, random, json
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
import numpy as np
from av_gk_lib import cidx, ks, ioc1
from lib import KA, AZ, CT, PT

Q = np.load('quadgrams.npy')
def qscore(idxs):
    a = np.asarray(idxs)
    k = ((a[:-3]*26 + a[1:-2])*26 + a[2:-1])*26 + a[3:]
    return float(Q.ravel()[k].mean())

def residual(ct, alpha, sign, primer, rec='aca', mod=10):
    c = cidx(ct, alpha)
    k = np.array(ks(primer, len(c), rec, mod))
    return (c + sign*k) % 26

def climb(res, iters=40000, restarts=8, seed=0):
    rng = random.Random(seed); best = -99; bestkey=None
    for r in range(restarts):
        key = list(range(26)); rng.shuffle(key)
        cur = qscore(np.array(key)[res])
        for it in range(iters):
            i, j = rng.randrange(26), rng.randrange(26)
            if i == j: continue
            key[i], key[j] = key[j], key[i]
            s = qscore(np.array(key)[res])
            if s > cur: cur = s
            else: key[i], key[j] = key[j], key[i]
        if cur > best: best, bestkey = cur, list(key)
    return best, bestkey

ENG = np.array([8.167,1.492,2.782,4.253,12.702,2.228,2.015,6.094,6.966,0.153,0.772,4.025,2.406,
                6.749,7.507,1.929,0.095,5.987,6.327,9.056,2.758,0.978,2.360,0.150,1.974,0.074])/100
ENGS = np.sort(ENG)[::-1]
def profile_fit(res):
    """Transposition-INVARIANT: sorted unigram profile vs English sorted profile (chi2, lower=better)."""
    n = len(res)
    p = np.sort(np.bincount(res, minlength=26))[::-1] / n
    return float((((p - ENGS)**2) / ENGS).sum())

out = {}
res = residual(CT['pk9'], KA, -1, [2,5,4,6,7,5,4])
out['claimed'] = {'ioc': ioc1(res), 'profile_chi2': profile_fit(res)}
print('CLAIMED HIT  ioc=%.6f  sorted-profile chi2=%.4f' % (out['claimed']['ioc'], out['claimed']['profile_chi2']))
q, key = climb(res, seed=1)
out['claimed']['climb_q'] = q
print('  monoalphabetic hill-climb quadgram/letter = %.4f   (English -4.25, random -8.23)' % q)
print('  decrypt:', ''.join(AZ[c] for c in np.array(key)[res]))

# --- reference: a REAL monoalphabetic image of real English of the same length ---
print()
ref = []
for i in range(6):
    rng = random.Random(500+i); mix = list(range(26)); rng.shuffle(mix)
    src = PT['pk1'][:144]
    r = np.array([mix[AZ.index(ch)] for ch in src])
    qq,_ = climb(r, seed=10+i)
    ref.append((ioc1(r), profile_fit(r), qq))
    print('REF mono-image of English n=144: ioc=%.6f chi2=%.4f climb=%.4f' % ref[-1])
out['reference_english'] = ref

# --- matched nulls: same statistic on the best-of-search residual from shuffled pk9 ---
print()
print('(matched-null residuals are produced by av_null.py; see av_gromark_resid.py)')
json.dump(out, open('results/av_gromark_autopsy.json','w'), indent=1)
