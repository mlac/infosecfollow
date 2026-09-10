"""rv_pc.py -- INDEPENDENT positive control: does MY kernel recover a true Gromark primer
at n=144 (pk9's length), form C = MIX(P) + k, with and without a width-9 columnar underneath?
Synthetic built here with my own code, not gk_common.make_syn."""
import sys, json, time
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
import numpy as np
from rv_kern import to_ct_idx, enumerate_full, keystream_rows, score_rows
from lib import KA, AZ, PT, col_enc

TRUE = [4, 1, 9, 0, 3, 7, 2]          # verifier's own primer, not the claim's
rng = np.random.default_rng(424242)
MIX = rng.permutation(26)             # unknown mixed alphabet

def make(pt, primer, alpha, perm=None):
    txt = col_enc(pt, perm) if perm else pt
    n = len(txt)
    k = keystream_rows(np.array([primer], np.uint8), n, 'aca', 10)[0].astype(int)
    p = to_ct_idx(txt, alpha).astype(int)
    return ''.join(alpha[(MIX[p[i]] + k[i]) % 26] for i in range(n))

base = ''.join(ch for ch in PT['pk1'] if ch.isalpha())[:144]
assert len(base) == 144
out = {}
for tag, perm in [('plain', None), ('col9', tuple(np.random.default_rng(7).permutation(9).tolist()))]:
    ct = make(base, TRUE, KA, perm)
    c = to_ct_idx(ct, KA)
    t = time.time()
    b, p, m, sd, cnt = enumerate_full(c, 7, 10, 'aca', -1, chunk=200000)
    rank = None
    for i in range(len(b)):
        if list(p[i]) == TRUE: rank = i + 1
    out[tag] = {'n': len(ct), 'true_primer': TRUE, 'true_rank': rank,
                'top1_score': float(b[0]), 'top1_primer': [int(x) for x in p[0]],
                'top2_score': float(b[1]), 'per_primer_mean': float(m), 'per_primer_sd': float(sd),
                'sec': round(time.time() - t, 1)}
    print(tag, out[tag], flush=True)
json.dump(out, open('results/rv_gromark_pc.json', 'w'), indent=1)
