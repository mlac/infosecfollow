"""ADVERSARIAL VERIFY, frontier item 5.
Rebuild the dual-beam matched null for the PK10 kmin>=8 cell FROM SCRATCH,
running the IDENTICAL beam in EVERY MODE the real search maximised over
(add/sub/beau), on the SAME shuffle seeds the published null used (1000+s).

The published null (results/wb_dual_null_k8.json, wb_run_null.py) ran mode='add'
ONLY, then compared a mode='beau' real cell against it.  If the mode changes the
achievable objective, that null is not matched.
"""
import sys, json, time, numpy as np; sys.path.insert(0,'.')
from lib import KA, CT, qscore
import wb_core as W

S0, S1, TAG = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
alpha = KA; ai = {c:i for i,c in enumerate(alpha)}
QGM = W.qg_matrix(alpha); BEAM = 100000; KMIN = 8
w,l = W.load_vocab(3,16);    tp = W.build_trie(w,l,alpha)
w,l = W.load_vocab(KMIN,16); tk = W.build_trie(w,l,alpha)
base = np.array([ai[c] for c in CT['pk10']], dtype=np.int64)
print(f'vocab pt={len(tp[1])} nodes  key kmin={KMIN}', flush=True)

out=[]
for s in range(S0,S1):
    rng = np.random.default_rng(1000+s)          # SAME seeds as wb_run_null.py
    c = base.copy(); rng.shuffle(c)
    row = {'shuffle': s}
    for mode in ('add','sub','beau'):
        r = W.dual_beam(c, tp, QGM, mode=mode, beam=BEAM, Wpt=1.0, Wkey=2.0, trie_key=tk)
        pt, key = W.decode_path(r['path'], c, mode, alpha)
        row[mode] = round(r['score'],4); row[mode+'_qg'] = round(qscore(pt),4)
        row[mode+'_sec'] = round(r['sec'],1)
        print(f"  sh{s:2d} {mode:4s} obj={r['score']:8.4f} qg={qscore(pt):7.4f} {r['sec']:.0f}s", flush=True)
    row['max3'] = max(row['add'], row['sub'], row['beau'])
    row['argmax3'] = max(('add','sub','beau'), key=lambda m: row[m])
    out.append(row)
    json.dump(out, open(f'results/av5_null_{TAG}.json','w'), indent=1)
print('DONE', TAG, flush=True)
