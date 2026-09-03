"""Autopsy for Gromark cells that beat their matched-null ceiling.

For each hit: rebuild the keystream, peel it, print the residual, its IoC against the English
band for that n, and run a monoalphabetic hill-climb on the residual (the residual is supposed
to be MIX(plaintext) -- if the primer were right, a monoalphabetic solve must produce English).
Reports the hill-climb quadgram score against the same climb run on shuffled residuals.
"""
import sys, json, random, numpy as np
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
from gk_common import *
from lib import qscore, load_quadgrams, AZ

QG = load_quadgrams()

def hillclimb(res_idx, iters=6000, restarts=3, seed=0):
    r = random.Random(seed)
    a = np.array(res_idx, dtype=np.int64)
    best = (-99, None)
    for _ in range(restarts):
        key = list(range(26)); r.shuffle(key)
        cur = qscore(np.array([key[v] for v in a]), QG)
        for _ in range(iters):
            i, j = r.randrange(26), r.randrange(26)
            if i == j: continue
            key[i], key[j] = key[j], key[i]
            s = qscore(np.array([key[v] for v in a]), QG)
            if s > cur: cur = s
            else: key[i], key[j] = key[j], key[i]
        if cur > best[0]: best = (cur, list(key))
    return best

def residual(ct_str, alpha, sign, primer, rec, mod):
    n = len(ct_str)
    k = keystream(primer, n, rec, mod)
    c = idx(ct_str, alpha)
    return [(c[i] + sign * k[i]) % 26 for i in range(n)]

ENG = {144: (0.0562, 0.0640, 0.0728), 153: (0.0560, 0.0640, 0.0725), 504: (0.0602, 0.0643, 0.0684)}

def main():
    d = json.load(open('results/gromark_running_key.json'))
    hits = sorted([h for h in d['above_ceiling'] if h['stat'] == 'IOC'],
                  key=lambda x: -x['z_vs_null_best'])[:8]
    seen = {h['cell'] + h['run'] for h in hits}
    for b in d['per_ct_best'].values():          # always autopsy the strongest cell per ciphertext
        if b['cell'] + b['run'] not in seen: hits.append(b)
    print("AUTOPSY of %d above-ceiling shift-IoC cells\n" % len(hits))
    rows = []
    for h in hits:
        ct, _, rest = h['cell'].split('.', 2)
        aname, sname = rest.split('.')
        alpha = KA if aname == 'KA' else AZ
        sg = -1 if sname == 'm' else +1
        rec = [k for k, v in RECS.items() if v == h['recur']][0]
        r = residual(CT[ct], alpha, sg, h['primer'], rec, h['mod'])
        rs = ''.join(AZ[v] for v in r)
        io = ioc(rs)
        p5, mean, p95 = ENG[h['n']]
        q, key = hillclimb(r, seed=hash(h['cell']) & 0xffff)
        # matched null for the hill-climb: same climb on shuffled residuals
        nulls = []
        for s in range(2):
            rr = list(r); random.Random(100 + s).shuffle(rr)
            nulls.append(hillclimb(rr, seed=s)[0])
        rows.append({'cell': h['cell'], 'run': h['run'], 'primer': h['primer'],
                     'ioc': io, 'eng_p5': p5, 'z_vs_null_best': h['z_vs_null_best'],
                     'monoalpha_q': round(q, 3), 'monoalpha_q_null_max': round(max(nulls), 3),
                     'residual': rs})
        print("%s  %s" % (h['run'], h['cell']))
        print("   primer=%s  IoC=%.5f  (English n=%d p5=%.4f mean=%.4f)  z_vs_nullbest=%+.2f"
              % (h['primer'], io, h['n'], p5, mean, h['z_vs_null_best']))
        print("   monoalpha hill-climb quadgram/letter = %.3f  (same climb on shuffled residual: max %.3f; English -4.25)"
              % (q, max(nulls)))
        print("   residual[:80] = %s\n" % rs[:80])
    json.dump(rows, open('results/gromark_autopsy.json', 'w'), indent=1)
    print("WROTE results/gromark_autopsy.json")

if __name__ == '__main__':
    main()
