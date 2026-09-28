"""Is the claimed residual's English-looking sorted-unigram profile anything BEYOND its IoC?
Null: random 26-letter count vectors of length 144 with IoC matched to the hit's 0.06371.
Reference: genuine (mixed-alphabet) English at n=144."""
import sys, numpy as np
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
from lib import PT, AZ
ENG = np.array([.08167,.01492,.02782,.04253,.12702,.02228,.02015,.06094,.06966,.00153,
                .00772,.04025,.02406,.06749,.07507,.01929,.00095,.05987,.06327,.09056,
                .02758,.00978,.02360,.00150,.01974,.00074])
ES = np.sort(ENG)[::-1]
def chi2(cnt):
    p = np.sort(cnt / cnt.sum())[::-1]
    return float((((p - ES) ** 2) / ES).sum())
def ioc_of(cnt):
    n = cnt.sum(); return float((cnt * (cnt - 1)).sum() / (n * (n - 1)))
rng = np.random.default_rng(5150)
keep = []
while len(keep) < 3000:
    a = rng.uniform(0.15, 3.0)
    p = rng.dirichlet(np.full(26, a))
    cnt = rng.multinomial(144, p)
    if 0.0630 <= ioc_of(cnt) <= 0.0645: keep.append(chi2(cnt))
keep = np.array(keep)
print('IoC-matched random-multiset null (n=%d): profile chi2 mean %.4f sd %.4f  p5 %.4f p50 %.4f p95 %.4f'
      % (len(keep), keep.mean(), keep.std(), *np.percentile(keep, [5, 50, 95])))
print('CLAIMED residual profile chi2 = 0.0984  -> percentile %.1f%%' % (100 * (keep < 0.0984).mean()))
eng = []
for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7']:
    s = ''.join(c for c in PT[k] if c.isalpha())
    for st in range(0, len(s) - 144, 37):
        c = np.bincount([AZ.index(ch) for ch in s[st:st+144]], minlength=26)
        eng.append((chi2(c), ioc_of(c)))
e = np.array(eng)
print('genuine English n=144 (%d windows): profile chi2 mean %.4f sd %.4f  (IoC mean %.4f)'
      % (len(e), e[:,0].mean(), e[:,0].std(), e[:,1].mean()))
print('  fraction of English windows with chi2 <= 0.0984: %.2f' % (e[:,0] <= 0.0984).mean())
