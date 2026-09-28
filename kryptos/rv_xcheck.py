"""Cross-check: recompute, with MY kernel, the stored top-1 score of every shift-IoC cell in the
full-enumeration artifacts, from the stored primer. Any mismatch means the two kernels do not
implement the same statistic (and my null would not be matched)."""
import sys, json, random
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
import numpy as np
from rv_kern import to_ct_idx, keystream_rows, score_rows
from lib import KA, AZ, CT

def shuffled(s, seed):
    r = random.Random(seed); l = list(s); r.shuffle(l); return ''.join(l)
COPY = {'real': None, 'nul1': 1001, 'nul2': 2002}
ALPHA = {'KA': KA, 'AZ': AZ}
SIGN = {'m': -1, 'p': +1}
bad = tot = 0; worst = 0.0
for f in ['results/gromark_L7_mod10.json'] + ['results/gromark_L8_mod10_r%d.json' % i for i in range(4)]:
    for r in json.load(open(f)):
        for name, t in r['targets'].items():
            ct, copy, rest = name.split('.')[0], name.split('.')[1], '.'.join(name.split('.')[2:])
            if rest == 'CLS': continue
            aname, sname = rest.split('.')
            s = CT[ct] if COPY[copy] is None else shuffled(CT[ct], COPY[copy])
            c = to_ct_idx(s, ALPHA[aname])
            P = np.array([t['top'][0]['primer']], np.uint8)
            K = keystream_rows(P, len(c), r['rec'], r['mod'])
            mine = float(score_rows(c, K, SIGN[sname])[0])
            d = abs(mine - t['top'][0]['score']); worst = max(worst, d); tot += 1
            if d > 5e-7: bad += 1; print('MISMATCH', f, name, r['rec'], t['top'][0]['score'], mine)
print('cross-checked %d shift-IoC cells from the full-enumeration artifacts; mismatches=%d; worst |diff|=%.2e (artifact scores are stored to 6 dp)' % (tot, bad, worst))
