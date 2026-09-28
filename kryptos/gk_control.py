"""POSITIVE CONTROLS for the Gromark family: can the primer sweep recover its own synthetics?"""
import sys, time, json
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
from gk_common import *

EN = ''.join(PT[k] for k in ['pk6', 'pk1', 'pk3', 'pk7', 'pk2'])
PERM9 = (4, 0, 7, 2, 8, 1, 5, 3, 6)

def controls_for(L, mod, rec, lengths=(144, 153, 504), primer=None):
    mix = mixalpha(7)
    primer = primer or [(3 * i + 5) % mod for i in range(L)]
    spec = []
    truth = {}
    for n in lengths:
        pt = EN[:n]
        # form A, plain (no transposition), arithmetic in A-Z
        s = make_syn(pt, primer, rec, mod, mix, AZ, 'A', +1)
        spec.append(target('synA%d' % n, 0, -1, idx(s, AZ)))
        truth['synA%d' % n] = primer
        # form A with a width-9 columnar UNDERNEATH, arithmetic in KA
        pt9 = pt[:(n // 9) * 9]
        s = make_syn(pt9, primer, rec, mod, mix, KA, 'A', +1, perm=PERM9)
        spec.append(target('synAcol%d' % n, 0, -1, idx(s, KA)))
        truth['synAcol%d' % n] = primer
    # form B = true ACA Gromark (mix AFTER the shift), only class-IoC can see it
    s = make_syn(EN[:504], primer, rec, mod, mix, AZ, 'B', +1)
    spec.append(target('synB504', 1, 0, idx(s, AZ)))
    truth['synB504'] = primer
    return ''.join(spec), truth, primer

def report(res, truth, tag):
    rows = []
    for name, tr in truth.items():
        t = res['targets'][name]
        top = t['top']
        rank = next((i for i, e in enumerate(top) if e['primer'] == tr), None)
        z = (top[0]['score'] - t['mean']) / t['sd'] if t['sd'] > 0 else 0
        ztrue = None
        if rank is not None:
            ztrue = (top[rank]['score'] - t['mean']) / t['sd']
        rows.append({'tag': tag, 'target': name, 'n': t['n'], 'searched': t['count'],
                     'rank_of_true': rank, 'best_score': top[0]['score'],
                     'best_primer': top[0]['primer'], 'true_primer': tr,
                     'null_mean': t['mean'], 'null_sd': t['sd'],
                     'z_best': round(z, 2), 'z_true': round(ztrue, 2) if ztrue is not None else None})
        print("  %-22s n=%3d rank_of_true=%s  best=%.4f z=%.1f" %
              (name, t['n'], rank, top[0]['score'], z), flush=True)
    return rows

if __name__ == '__main__':
    L = int(sys.argv[1]); mod = int(sys.argv[2]); recs = [int(x) for x in sys.argv[3].split(',')]
    allrows = []
    for rec in recs:
        spec_t, truth, primer = controls_for(L, mod, rec)
        sp = header(mod, L, 504, rec, topk=8, enum=1) + spec_t
        t0 = time.time()
        print("L=%d mod=%d rec=%s primer=%s" % (L, mod, RECS[rec], primer), flush=True)
        res = run(sp, '/tmp/claude-0/-home-user-infosecfollow/88072dfe-db0a-5acd-9caa-27f75aea8fde/scratchpad/ctl.spec')
        print("  executed=%d  %.1fs" % (res['executed'], time.time() - t0), flush=True)
        allrows += report(res, truth, 'L%d_mod%d_%s' % (L, mod, RECS[rec]))
    json.dump(allrows, open('results/gromark_controls_L%d_mod%d.json' % (L, mod), 'w'), indent=1)
