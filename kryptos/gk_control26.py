"""Positive control for the mod-26 (letter) running-key generator with WORD primers."""
import sys, json, time
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
from gk_common import *
from gk_control import EN, PERM9
from gk_sweep import wordprimers

def go(L, word, recs, mod=26):
    rows = []
    for aname, alpha in [('KA', KA), ('AZ', AZ)]:
        pl, ws = wordprimers(L, alpha)
        if mod == 10: pl = [[v % 10 for v in p] for p in pl]
        assert word in ws, word
        pw = pl[ws.index(word)]
        mix = mixalpha(11)
        for rec in recs:
            spec, truth = [], {}
            for n in (144, 153, 504):
                s = make_syn(EN[:n], pw, rec, mod, mix, AZ, 'A', +1)
                spec.append(target('synA%d' % n, 0, -1, idx(s, AZ)))
                truth['synA%d' % n] = pw
            pt9 = EN[:504]
            s = make_syn(pt9, pw, rec, mod, mix, KA, 'A', +1, perm=PERM9)
            spec.append(target('synAcol504', 0, -1, idx(s, KA)))
            truth['synAcol504'] = pw
            res = run(header(mod, L, 504, rec, topk=8, enum=0, primers=pl) + ''.join(spec),
                      '/tmp/claude-0/-home-user-infosecfollow/88072dfe-db0a-5acd-9caa-27f75aea8fde/scratchpad/c26.spec')
            for name, tr in truth.items():
                t = res['targets'][name]
                rank = next((i for i, e in enumerate(t['top']) if e['primer'] == tr), None)
                bw = ws[pl.index(t['top'][0]['primer'])] if t['top'][0]['primer'] in pl else '?'
                z = (t['top'][0]['score'] - t['mean']) / t['sd']
                rows.append({'L': L, 'mod': mod, 'rec': RECS[rec], 'primer_alpha': aname,
                             'target': name, 'n': t['n'], 'searched': t['count'],
                             'true_word': word, 'rank_of_true': rank,
                             'best_word': bw, 'best_score': t['top'][0]['score'],
                             'z_best': round(z, 2)})
                print("  L=%d %s %-6s %-12s n=%3d rank=%s best=%s %.4f z=%.1f" %
                      (L, aname, RECS[rec], name, t['n'], rank, bw, t['top'][0]['score'], z), flush=True)
    return rows

if __name__ == '__main__':
    rows = go(7, 'NEEDLES', [0, 1, 2, 3]) + go(8, 'ORDINATE', [0, 1, 2, 3])
    rows += go(7, 'NEEDLES', [0, 1, 2, 3], mod=10) + go(8, 'ORDINATE', [0, 1, 2, 3], mod=10)
    json.dump(rows, open('results/gromark_controls_words.json', 'w'), indent=1)
    print("WROTE results/gromark_controls_words.json")
