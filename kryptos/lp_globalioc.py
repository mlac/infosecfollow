"""Independent cross-check: whole-text IoC vs what a period-p polyalphabetic produces.

Whole-text IoC is invariant to any transposition AND to the per-class substitutions, so
this is a second, independent handle on the same family. A period-p polyalphabetic drives
whole-text IoC down toward random (0.0385 + ~0.026/p). PK9's whole-text IoC is ELEVATED
(0.0445), which is the wrong direction for any long period.
"""
import numpy as np, sys, json; sys.path.insert(0,'.')
from lib import CT, PT
from lp_ioc import idx
from lp_prof import prof_score  # noqa
RNG = np.random.default_rng(99)
ENG = idx(''.join(PT[k] for k in PT))

def gioc(a):
    c = np.bincount(a, minlength=26).astype(float); n = len(a)
    return (c*(c-1)).sum()/(n*(n-1))

out = {}
for name, n in [('pk8',153),('pk9',144),('pk10',504)]:
    obs = gioc(idx(CT[name]))
    rec = {'obs': round(obs,5), 'by_period': {}}
    for p in [25,35,45,55,72]:
        v = []
        for _ in range(3000):
            st = RNG.integers(0, len(ENG)-n); t = ENG[st:st+n]
            t = RNG.permutation(t)                      # unknown columnar underneath
            k = RNG.integers(0,26,size=p)
            v.append(gioc((t + k[np.arange(n)%p])%26))
        v = np.array(v)
        rec['by_period'][p] = dict(sim_mean=round(v.mean(),5), sim_sd=round(v.std(),5),
                                   z_obs=round(float((obs-v.mean())/v.std()),2),
                                   p_two_sided=round(float(2*min((v>=obs).mean(),(v<=obs).mean())),4))
    out[name] = rec
    print(name, 'obs IoC', round(obs,5), {p: (r['sim_mean'], r['z_obs'], r['p_two_sided'])
                                          for p,r in rec['by_period'].items()}, flush=True)
json.dump(out, open('results/lp_globalioc.json','w'), indent=1)
