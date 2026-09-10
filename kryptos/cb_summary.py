"""Aggregate the crib-attack family: real vs MATCHED null, test by test."""
import json, glob, sys, numpy as np
R = json.load(open('results/cb_main_real.json'))
N = json.load(open('results/cb_main_null6.json'))
out = {'battery': {}, 'columnar': {}, 'cross_target': {}}

def stat(d):
    return {'rows': d['rows'], 'periodic': len(d['periodic']), 'affine': len(d['affine']),
            'fib': len(d['fib']), 'linear': len(d['linear']), 'w1': d['n_w1'], 'w2': d['n_w2'],
            'seg': d['n_seg'], 'sibling': len(d['sibling']), 'engmax': d['eng_best'][0],
            'engmean': d['eng_mean'], 'lin_tests': d['lin_tests'], 'lin_efp': d['lin_efp'],
            'word_tests': d['word_tests']}

real = {t: stat(v) for t, v in R['per_text'].items()}
nulls = {}
for k, v in N['per_text'].items():
    tag = k.split('_shuf')[0]
    nulls.setdefault(tag, []).append(stat(v))
KEYS = ['periodic', 'affine', 'fib', 'linear', 'w1', 'w2', 'seg', 'sibling', 'engmax']
print(f"{'target':6s} {'test':9s} {'REAL':>10s} {'null mean':>10s} {'null max':>9s} "
      f"{'n_null':>6s}  verdict")
tot = {'rows': 0, 'lin_tests': 0, 'word_tests': 0, 'lin_efp': 0.0}
for t in real:
    for k in ['rows', 'lin_tests', 'word_tests', 'lin_efp']: tot[k] += real[t][k]
    for key in KEYS:
        nv = [n[key] for n in nulls.get(t, [])]
        rv = real[t][key]
        above = (rv > max(nv)) if nv else None
        print(f"{t:6s} {key:9s} {rv:10.4g} {np.mean(nv):10.4g} {max(nv):9.4g} {len(nv):6d}  "
              f"{'ABOVE NULL MAX' if above else 'at/below null'}")
    out['battery'][t] = {'real': real[t], 'null_mean': {k: float(np.mean([n[k] for n in nulls[t]]))
                         for k in KEYS}, 'null_max': {k: float(max(n[k] for n in nulls[t]))
                         for k in KEYS}, 'n_null': len(nulls[t])}
out['totals'] = tot
print("\nTOTALS (real):", {k: (f"{v:,}" if isinstance(v, int) else round(v, 3)) for k, v in tot.items()})
for f, key in (('results/cb_col_real.json', 'columnar'), ('results/cb_pair_real.json', 'cross_target')):
    try:
        d = json.load(open(f))
        out[key] = d
    except Exception as e:
        out[key] = {'error': str(e)}
json.dump(out, open('results/crib_attacks_summary.json', 'w'), indent=1, default=str)
print("\nwrote results/crib_attacks_summary.json")
