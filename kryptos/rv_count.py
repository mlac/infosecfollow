"""rv_count.py -- independent recount of executed cells + independent pooled matched-null.
Reads only the raw sweep artifacts; does not use gk_analyze.py's output."""
import sys, json, glob, os, math
from collections import defaultdict

runs = []
for f in sorted(glob.glob('results/gromark_L*_mod*.json') + glob.glob('results/gromark_words_L*.json')):
    if 'controls' in f: continue
    for r in json.load(open(f)):
        r['file'] = os.path.basename(f); runs.append(r)

real, null = [], []
trials = 0
for r in runs:
    ex = r['executed']
    for name, t in r['targets'].items():
        copy = name.split('.')[1]
        stat = 'CLS' if name.endswith('CLS') else 'IOC'
        rec = {'cell': name, 'ct': name.split('.')[0], 'copy': copy, 'stat': stat,
               'n': t['n'], 'ex': ex, 'best': t['top'][0]['score'],
               'primer': t['top'][0]['primer'], 'ppmean': t['mean'], 'ppsd': t['sd'],
               'file': r['file'], 'L': r['L'], 'mod': r['mod'], 'rec': r['rec'], 'tag': r.get('tag','')}
        (real if copy == 'real' else null).append(rec)
        trials += ex
print('runs=%d  REAL cells=%d  NULL cells=%d  total trial decryptions=%.4g'
      % (len(runs), len(real), len(null), trials))
byfile = defaultdict(lambda: [0,0])
for x in real: byfile[x['file']][0] += 1
for x in null: byfile[x['file']][1] += 1
for f in sorted(byfile): print('   %-34s real=%3d null=%3d' % (f, *byfile[f]))

pool = defaultdict(list)
for x in null: pool[(x['n'], x['stat'], x['ex'])].append(x['best'])
print('\nPOOLED MATCHED NULL (best-of-search), independently rebuilt from artifacts:')
stats = {}
for k in sorted(pool):
    b = sorted(pool[k]); m = sum(b)/len(b)
    sd = math.sqrt(sum((v-m)**2 for v in b)/len(b))
    stats[k] = (len(b), m, sd, b[-1])
    print('   n=%3d %s exec=%-10d searches=%2d mean=%.5f sd=%.5f MAX=%.5f' % (k[0],k[1],k[2],len(b),m,sd,b[-1]))

above = []
for x in real:
    s = stats.get((x['n'], x['stat'], x['ex']))
    if not s: continue
    if x['best'] > s[3]:
        z = (x['best']-s[1])/s[2] if s[2] else 0
        above.append((z, x, s))
exp = sum(1.0/(1+stats[(x['n'],x['stat'],x['ex'])][0]) for x in real if (x['n'],x['stat'],x['ex']) in stats)
print('\nABOVE POOLED NULL MAX: %d of %d real cells; expected by chance = %.2f'
      % (len(above), sum(1 for x in real if (x['n'],x['stat'],x['ex']) in stats), exp))
for z, x, s in sorted(above, key=lambda t:-t[0])[:12]:
    print('   z=%+5.2f %-16s best=%.6f nullmax=%.6f exec=%-10d %s L=%d mod=%d rec=%s %s primer=%s'
          % (z, x['cell'], x['best'], s[3], x['ex'], x['file'], x['L'], x['mod'], x['rec'], x['tag'], x['primer']))

# comparable-scale cells for the claimed hit: n=144, IOC statistic, full enumerations >= 1e7
comp = [x for x in real if x['n']==144 and x['stat']=='IOC' and x['ex']>=10**7]
print('\nCOMPARABLE-SCALE REAL CELLS (n=144, shift-IoC, exec>=1e7): %d' % len(comp))
for x in sorted(comp, key=lambda t:-t['best'])[:8]:
    print('   %.6f %-16s exec=%-10d L=%d mod=%d rec=%s' % (x['best'],x['cell'],x['ex'],x['L'],x['mod'],x['rec']))
json.dump({'real_cells': len(real), 'null_cells': len(null), 'trials': trials,
           'n144_ioc_ge1e7_real_cells': len(comp)}, open('results/rv_counts.json','w'), indent=1)
