"""Pooled matched-null analysis for the Gromark / running-key sweeps.

Per-cell "real beat its own 2 null draws" is worthless (P=1/3 by construction).
The right ceiling is the distribution of BEST-OF-SEARCH over matched null searches of the
same (statistic, length, search size).  Every null search is an identical primer enumeration
over a letter-shuffled copy of the same ciphertext.
"""
import sys, json, glob, math, os
sys.path.insert(0, '/home/user/infosecfollow/kryptos')

CTS = ['pk8', 'pk9', 'pk10']

def load():
    runs = []
    for f in sorted(glob.glob('results/gromark_L*_mod*.json') + glob.glob('results/gromark_words_L*.json')):
        if 'controls' in f: continue
        for r in json.load(open(f)):
            r['file'] = f
            runs.append(r)
    return runs

def cellname(t):
    p = t.split('.')
    return p[0], p[1], '.'.join(p[2:])

def main():
    runs = load()
    # pool: key = (n, statistic, executed)   statistic = 'CLS' or 'IOC'
    pool = {}
    reals = []
    for r in runs:
        ex = r['executed']
        for name, t in r['targets'].items():
            ct, copy, rest = cellname(name)
            stat = 'CLS' if rest == 'CLS' else 'IOC'
            key = (t['n'], stat, ex)
            rec = {'run': '%s L=%d mod=%d rec=%s %s' % (os.path.basename(r['file']), r['L'], r['mod'], r['rec'], r.get('tag', '')),
                   'cell': name, 'ct': ct, 'n': t['n'], 'stat': stat, 'executed': ex,
                   'best': t['top'][0]['score'], 'primer': t['top'][0]['primer'],
                   'mean': t['mean'], 'sd': t['sd'], 'key': key,
                   'L': r['L'], 'mod': r['mod'], 'recur': r['rec'], 'tag': r.get('tag', '')}
            if copy == 'real':
                reals.append(rec)
            else:
                pool.setdefault(key, []).append(rec)
    stats = {}
    for k, v in pool.items():
        b = sorted(x['best'] for x in v)
        m = sum(b) / len(b)
        sd = math.sqrt(sum((x - m) ** 2 for x in b) / len(b)) if len(b) > 1 else 0.0
        stats[k] = {'n_null_searches': len(b), 'null_best_mean': m, 'null_best_sd': sd,
                    'null_best_max': b[-1], 'null_best_min': b[0]}
    out = {'pooled_null': [], 'above_ceiling': [], 'per_ct_best': {}, 'all_real': []}
    for k, s in sorted(stats.items()):
        out['pooled_null'].append({'n': k[0], 'stat': k[1], 'executed': k[2], **s})
    for r in reals:
        s = stats.get(r['key'])
        if not s: continue
        z = (r['best'] - s['null_best_mean']) / s['null_best_sd'] if s['null_best_sd'] else 0.0
        r['null_best_max'] = s['null_best_max']; r['null_best_mean'] = s['null_best_mean']
        r['null_best_sd'] = s['null_best_sd']; r['n_null_searches'] = s['n_null_searches']
        r['z_vs_null_best'] = round(z, 2)
        r['above_ceiling'] = r['best'] > s['null_best_max']
        out['all_real'].append({kk: vv for kk, vv in r.items() if kk != 'key'})
        if r['above_ceiling']:
            out['above_ceiling'].append({kk: vv for kk, vv in r.items() if kk != 'key'})
    for ct in CTS:
        cand = [r for r in reals if r['ct'] == ct and r['stat'] == 'IOC']
        if not cand: continue
        b = max(cand, key=lambda x: x['best'])
        out['per_ct_best'][ct] = {kk: vv for kk, vv in b.items() if kk != 'key'}
    json.dump(out, open('results/gromark_running_key.json', 'w'), indent=1)

    print("POOLED MATCHED NULL (best-of-search over letter-shuffled copies)")
    for p in out['pooled_null']:
        print("  n=%3d %s exec=%-9d searches=%2d  null best-of-search: mean %.5f sd %.5f MAX %.5f" %
              (p['n'], p['stat'], p['executed'], p['n_null_searches'],
               p['null_best_mean'], p['null_best_sd'], p['null_best_max']))
    print("\nBEST REAL CELL PER CIPHERTEXT (shift-IoC statistic)")
    for ct, b in out['per_ct_best'].items():
        print("  %-5s best IoC %.5f  (%s %s)  pooled null max %.5f  z=%+.2f  above=%s" %
              (ct, b['best'], b['run'], b['cell'], b['null_best_max'], b['z_vs_null_best'], b['above_ceiling']))
    exp = sum(1.0 / (1 + r['n_null_searches']) for r in out['all_real'])
    out['expected_above_by_chance'] = round(exp, 2)
    print("\nREAL CELLS ABOVE POOLED NULL MAX: %d of %d  (expected by chance if null==real: %.1f)"
          % (len(out['above_ceiling']), len(out['all_real']), exp))
    for h in sorted(out['above_ceiling'], key=lambda x: -x['z_vs_null_best'])[:20]:
        print("  %-58s %-16s best=%.5f nullmax=%.5f z=%+.2f primer=%s" %
              (h['run'], h['cell'], h['best'], h['null_best_max'], h['z_vs_null_best'], h['primer']))
    print("\nWROTE results/gromark_running_key.json")

if __name__ == '__main__':
    main()
