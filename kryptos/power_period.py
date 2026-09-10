"""DOCTRINE 2: what period would the transposition-invariant column-IoC test actually DETECT?
Without this power curve, 'we saw no period' means nothing."""
import numpy as np
from lib import *
rng = np.random.default_rng(31337)
ENG = ''.join(PT[k] for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7'])
def eng(n): i = rng.integers(0, len(ENG)-n); return ENG[i:i+n]

def colz(ct, p, nullpool):
    v = np.mean([ioc(ct[r::p]) for r in range(p) if len(ct[r::p]) > 3])
    return (v - nullpool[p][0]) / nullpool[p][1], v

def nullpool_for(ct, ps, R=600):
    """matched null: identical statistic on letter-shuffled copies of the SAME ciphertext"""
    out = {}
    L = list(ct)
    sh = [''.join(rng.permutation(L)) for _ in range(R)]
    for p in ps:
        v = [np.mean([ioc(s[r::p]) for r in range(p) if len(s[r::p]) > 3]) for s in sh]
        out[p] = (np.mean(v), np.std(v))
    return out

for tag, n in (('pk9',144), ('pk8',153), ('pk10',504)):
    ps = [p for p in range(2, 37) if n//p >= 5]
    np_real = nullpool_for(CT[tag], ps)
    print(f"\n=== {tag} n={n} ===")
    print(f"{'p':>3} {'obs z':>7} | POWER: z of a TRUE period-p cipher (100 sims)  detect@z>3")
    for p in ps:
        zo, vo = colz(CT[tag], p, np_real)
        zs = []
        for _ in range(100):
            pt = eng(n)
            k = rng.integers(0, 26, p)
            ct = to_str((to_idx(col_enc(pt,(6,2,3,5,1,4,0,7)))[:n] + k[np.arange(n)%p]) % 26)
            zs.append(colz(ct, p, np_real)[0])
        zs = np.array(zs)
        pw = (zs > 3).mean()
        mark = ''
        if pw > 0.8 and zo < 2: mark = '  <== period p EXCLUDED (test is powerful, saw nothing)'
        elif pw < 0.3: mark = '  <== test BLIND here'
        print(f"{p:3d} {zo:+7.2f} | true-cipher z mean {zs.mean():+6.2f} sd {zs.std():4.2f}  power {pw:.2f}{mark}")
