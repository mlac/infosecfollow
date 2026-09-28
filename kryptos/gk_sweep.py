"""Gromark / running-key primer sweep against pk8/pk9/pk10 with matched shuffle nulls.

Targets per run (fixed recurrence, modulus, primer length):
  mode 0 (shift-IoC): 3 ciphertexts x 3 copies (real + 2 letter-shuffles) x 2 text alphabets
                      (KA, A-Z) x 2 addition directions  = 36
  mode 1 (class-IoC): 3 ciphertexts x 3 copies                                   =  9
The shuffled copies ARE the matched null: identical primer enumeration, identical statistic,
identical length, same letter multiset.
"""
import sys, time, json, os
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
from gk_common import *

CTS = ['pk8', 'pk9', 'pk10']
COPIES = [('real', None), ('nul1', 1001), ('nul2', 2002)]
ALPHAS = [('KA', KA), ('AZ', AZ)]
SIGNS = [('m', -1), ('p', +1)]

def build_targets():
    nn = int(os.environ.get('GK_NULLS', '2'))
    cls = os.environ.get('GK_CLS', 'all')
    out = []
    for ct in CTS:
        for cname, seed in COPIES[:1 + nn]:
            s = CT[ct] if seed is None else shuffled(CT[ct], seed)
            for aname, alpha in ALPHAS:
                for sname, sg in SIGNS:
                    out.append(target('%s.%s.%s.%s' % (ct, cname, aname, sname), 0, sg, idx(s, alpha)))
            if cls == 'all' or (cls == 'pk10' and ct == 'pk10'):
                out.append(target('%s.%s.CLS' % (ct, cname), 1, 0, idx(s, AZ)))
    return ''.join(out)

def wordprimers(L, alpha):
    ws = [w for w in open('words.txt').read().split() if len(w) == L]
    ai = {c: i for i, c in enumerate(alpha)}
    return [[ai[c] for c in w] for w in ws], ws

def one(L, mod, rec, primers=None, tag=''):
    t0 = time.time()
    sp = header(mod, L, 504, rec, topk=8, enum=1 if primers is None else 0, primers=primers)
    res = run(sp + build_targets(), '/tmp/claude-0/-home-user-infosecfollow/88072dfe-db0a-5acd-9caa-27f75aea8fde/scratchpad/sw_%d_%d_%d.spec' % (L, mod, rec))
    res['L'] = L; res['mod'] = mod; res['rec'] = RECS[rec]; res['tag'] = tag
    res['sec'] = round(time.time() - t0, 1)
    print("== L=%d mod=%d rec=%s %s executed=%d %.0fs" %
          (L, mod, RECS[rec], tag, res['executed'], res['sec']), flush=True)
    # matched-null comparison, cell by cell
    cells = []
    for ct in CTS:
        for aname, _ in ALPHAS:
            for sname, _ in SIGNS:
                cells.append(('%s.%%s.%s.%s' % (ct, aname, sname), ct))
        if ('%s.real.CLS' % ct) in res['targets']:
            cells.append(('%s.%%s.CLS' % ct, ct))
    summary = []
    for pat, ct in cells:
        r = res['targets'][pat % 'real']
        nulls = [res['targets'][pat % c] for c, _ in COPIES[1:] if (pat % c) in res['targets']]
        nmax = max(x['top'][0]['score'] for x in nulls)
        nmean = sum(x['mean'] for x in nulls) / len(nulls)
        nsd = sum(x['sd'] for x in nulls) / len(nulls)
        z = (r['top'][0]['score'] - nmean) / nsd if nsd else 0
        summary.append({'cell': pat % 'real', 'n': r['n'],
                        'best': r['top'][0]['score'], 'best_primer': r['top'][0]['primer'],
                        'null_max': nmax, 'null_mean': nmean, 'null_sd': nsd,
                        'z_vs_null': round(z, 2), 'above_ceiling': r['top'][0]['score'] > nmax})
    res['summary'] = summary
    hits = [s for s in summary if s['above_ceiling']]
    best = max(summary, key=lambda s: s['best'])
    print("   best cell %s  best=%.5f null_max=%.5f z=%.2f | above-ceiling cells: %d" %
          (best['cell'], best['best'], best['null_max'], best['z_vs_null'], len(hits)), flush=True)
    for h in hits:
        print("   *** ABOVE CEILING %s best=%.5f > nullmax=%.5f primer=%s" %
              (h['cell'], h['best'], h['null_max'], h['best_primer']), flush=True)
    return res

if __name__ == '__main__':
    mode = sys.argv[1]
    out = []
    if mode == 'enum':
        L = int(sys.argv[2]); mod = int(sys.argv[3])
        for rec in [int(x) for x in sys.argv[4].split(',')]:
            out.append(one(L, mod, rec, tag='full-enumeration'))
        name = 'gromark_L%d_mod%d_r%s' % (L, mod, sys.argv[4].replace(',', ''))
    else:  # word-derived primers (mod 26 and mod 10 digit-encodings)
        L = int(sys.argv[2]); mod = int(sys.argv[3])
        for aname, alpha in ALPHAS:
            pl, ws = wordprimers(L, alpha)
            if mod == 10: pl = [[v % 10 for v in p] for p in pl]
            for rec in [int(x) for x in sys.argv[4].split(',')]:
                r = one(L, mod, rec, primers=pl, tag='word-primers-%s' % aname)
                r['primer_alpha'] = aname; r['nwords'] = len(ws)
                pmap = {tuple(p): w for p, w in zip(pl, ws)}
                for s in r['summary']:
                    s['best_word'] = pmap.get(tuple(s['best_primer']))
                out.append(r)
        name = 'gromark_words_L%d_mod%d' % (L, mod)
    json.dump(out, open('results/%s.json' % name, 'w'), indent=1)
    print("WROTE results/%s.json" % name, flush=True)
