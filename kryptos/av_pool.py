"""Independent reconstruction of the claim's pooled matched-null ceiling and the
above-ceiling count, plus a proper best-of-search multiple-testing correction."""
import json, glob, collections, math
import numpy as np

FILES = [f for f in sorted(glob.glob('results/gromark_*.json'))
         if not any(k in f for k in ('controls', 'autopsy', 'running_key'))]

real = []   # (key, cellname, score, primer)
null = collections.defaultdict(list)

for f in FILES:
    d = json.load(open(f))
    if not isinstance(d, list): d = [d]
    for r in d:
        if 'summary' not in r: continue
        nprim = r['executed']
        for t, tg in r['targets'].items():
            ct, copy, *rest = t.split('.')
            stat = 'CLS' if rest[-1] == 'CLS' else 'shift'
            n = tg['n']
            key = (n, stat, nprim)
            sc = tg['top'][0]['score']
            if copy == 'real':
                real.append((key, f, r.get('rec'), r.get('L'), t, sc, tuple(tg['top'][0]['primer']),
                             tg['mean'], tg['sd']))
            else:
                null[key].append(sc)

print('real cells %d  null cells %d' % (len(real), sum(len(v) for v in null.values())))
print()
print('%-28s %6s %6s %10s %10s' % ('pool (n,stat,nprimers)', 'nreal', 'nnull', 'null_max', 'real_max'))
above = []
for key in sorted(null):
    rs = [x for x in real if x[0] == key]
    ns = np.array(null[key])
    if not rs: continue
    nm = ns.max()
    rm = max(x[5] for x in rs)
    hit = [x for x in rs if x[5] > nm]
    above += hit
    print('%-28s %6d %6d %10.6f %10.6f  above=%d' % (str(key), len(rs), len(ns), nm, rm, len(hit)))

print()
print('ABOVE POOLED CEILING: %d of %d real cells' % (len(above), len(real)))
exp = sum(len([x for x in real if x[0] == k]) / (len(null[k]) + 1.0) for k in null if any(x[0]==k for x in real))
print('expected by chance (uniform rank argument): %.1f' % exp)
print()
for x in sorted(above, key=lambda y: -y[5])[:12]:
    print('  %-24s %-16s rec=%-6s L=%s  best=%.6f primer=%s' % (x[4], x[1].split('/')[-1], x[2], x[3], x[5], list(x[6])))

# ---- how the claim's own z_vs_null was computed ----
print()
print('=== z_vs_null forensics (top hit) ===')
d = json.load(open('results/gromark_L7_mod10.json'))
r = d[0]
tg = r['targets']['pk9.real.KA.m']
n1 = r['targets']['pk9.nul1.KA.m']; n2 = r['targets']['pk9.nul2.KA.m']
print('real best        %.6f' % tg['top'][0]['score'])
print('null1 per-primer mean %.6f sd %.6f  best-of-search %.6f' % (n1['mean'], n1['sd'], n1['top'][0]['score']))
print('null2 per-primer mean %.6f sd %.6f  best-of-search %.6f' % (n2['mean'], n2['sd'], n2['top'][0]['score']))
nm = (n1['mean']+n2['mean'])/2; ns = (n1['sd']+n2['sd'])/2
print('reported z_vs_null = (real_best - null PER-PRIMER mean)/PER-PRIMER sd = %.2f' %
      ((tg['top'][0]['score']-nm)/ns))
print(' -> numerator is a MAXIMUM over 10^7 draws; denominator is the sd of ONE draw.')
