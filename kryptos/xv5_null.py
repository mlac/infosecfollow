"""XV5 - INDEPENDENT ADVERSARIAL NULL, rebuilt from scratch.

The published null (wb_run_null.py -> results/wb_dual_null_k8.json) ran the dual
beam in mode='add' ONLY, on 8 shuffles, and the claimed best real cell is
mode='beau', KA, kmin>=8.  The real search maximised over 3 modes x 2 alphabets
x 3 key-vocabularies = 18 cells; each null replicate covered 1 cell.  That is a
multiple-comparison mismatch of exactly the kind that killed the earlier affine
z=+4.91.

This script rebuilds the null with FRESH seeds (55000+s, disjoint from the
published 1000+s and 2000+s) and makes each null REPLICATE the maximum over the
same 3 modes the real search maximised over at kmin>=8, KA.  That is still
CONSERVATIVE in the claim's favour (it does not include the AZ alphabet or the
kmin grid), so if the real cell fails here it fails a fortiori.
"""
import sys, json, numpy as np
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
from lib import KA, CT, qscore
import wb_core as W

S0, S1 = int(sys.argv[1]), int(sys.argv[2])
KMIN = int(sys.argv[3]) if len(sys.argv) > 3 else 8
alpha = KA; ai = {c: i for i, c in enumerate(alpha)}
QGM = W.qg_matrix(alpha); BEAM = 100000
w, l = W.load_vocab(3, 16);    tp = W.build_trie(w, l, alpha)
w, l = W.load_vocab(KMIN, 16); tk = W.build_trie(w, l, alpha)
base = np.array([ai[c] for c in CT['pk10']], dtype=np.int64)
print(f'XV5 null kmin={KMIN} beam={BEAM} shuffles {S0}..{S1-1} seeds 55000+s', flush=True)

fn = f'/home/user/infosecfollow/kryptos/results/xv5_null_k{KMIN}.json'
try:    out = json.load(open(fn))
except Exception: out = []
for s in range(S0, S1):
    rng = np.random.default_rng(55000 + s)
    c = base.copy(); rng.shuffle(c)
    row = {'shuffle': s, 'seed': 55000 + s, 'kmin': KMIN}
    for mode in ('add', 'sub', 'beau'):
        r = W.dual_beam(c, tp, QGM, mode=mode, beam=BEAM, Wpt=1.0, Wkey=2.0, trie_key=tk)
        pt, key = W.decode_path(r['path'], c, mode, alpha)
        row[mode] = round(r['score'], 4)
        row[mode + '_qg'] = round(qscore(pt), 4)
        print(f"  sh{s:2d} {mode:4s} obj={r['score']:8.4f} qg={qscore(pt):7.4f} {r['sec']:.0f}s", flush=True)
    row['max3'] = max(row['add'], row['sub'], row['beau'])
    row['argmax3'] = max(('add','sub','beau'), key=lambda m: row[m])
    row['max3_qg'] = max(row['add_qg'], row['sub_qg'], row['beau_qg'])
    out.append(row)
    json.dump(out, open(fn, 'w'), indent=1)
    m3 = np.array([x['max3'] for x in out])
    print(f"  -> sh{s} max3={row['max3']:.4f} ({row['argmax3']}) | running mean(max3)="
          f"{m3.mean():.4f} max={m3.max():.4f} n={len(m3)}", flush=True)
print('DONE', flush=True)
