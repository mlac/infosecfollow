"""XV5 - reproduce the claimed best dual-beam cell on real PK10 and audit it.
Claim: KA alphabet, key vocabulary len>=8, mode 'beau', beam 100,000 -> obj -6.4241,
quadgram -4.1858, described as the best of the 12 real cells.
Checks: (a) does the score reproduce bit-for-bit? (b) does re-encrypting the
recovered plaintext under the recovered key reproduce PK10 exactly?
(c) how long is the key relative to the plaintext it explains?
(d) does the plaintext read as English?
"""
import sys, json, time, numpy as np
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
from lib import KA, CT, qscore
import wb_core as W

alpha = KA; ai = {c: i for i, c in enumerate(alpha)}
QGM = W.qg_matrix(alpha); BEAM = 100000
MODES = sys.argv[1].split(',') if len(sys.argv) > 1 else ['beau']
KMIN = int(sys.argv[2]) if len(sys.argv) > 2 else 8
w, l = W.load_vocab(3, 16);    tp = W.build_trie(w, l, alpha)
w, l = W.load_vocab(KMIN, 16); tk = W.build_trie(w, l, alpha)
ct = CT['pk10']; c = np.array([ai[x] for x in ct], dtype=np.int64)
print(f'PK10 n={len(ct)} kmin={KMIN} beam={BEAM}', flush=True)

out = []
for mode in MODES:
    t0 = time.time()
    r = W.dual_beam(c, tp, QGM, mode=mode, beam=BEAM, Wpt=1.0, Wkey=2.0, trie_key=tk)
    pt, key = W.decode_path(r['path'], c, mode, alpha)
    pv = np.array([ai[x] for x in pt]); kv = np.array([ai[x] for x in key])
    # re-encrypt: add c=p+k ; sub c=p-k ; beau c=k-p
    if   mode == 'add':  cv2 = (pv + kv) % 26
    elif mode == 'sub':  cv2 = (pv - kv) % 26
    else:                cv2 = (kv - pv) % 26
    ct2 = ''.join(alpha[int(x)] for x in cv2)
    ob = W.objective(pt, key, tp, QGM, alpha, Wpt=1.0, Wkey=2.0, trie_key=tk)
    rec = dict(mode=mode, kmin=KMIN, obj=round(r['score'], 4), qg=round(qscore(pt), 4),
               sec=round(time.time() - t0, 1),
               roundtrip_exact=(ct2 == ct),
               n_pt=len(pt), n_key=len(key),
               key_words=ob['seg_key'], n_key_words=len(ob['seg_key']) if ob['seg_key'] else None,
               pt_words=ob['seg_pt'], n_pt_words=len(ob['seg_pt']) if ob['seg_pt'] else None,
               recomputed_obj=round(ob['obj'], 4), pt=pt, key=key)
    out.append(rec)
    print(f"[{mode}] obj={rec['obj']:.4f} (recomputed {rec['recomputed_obj']:.4f}) "
          f"qg={rec['qg']:.4f} roundtrip={rec['roundtrip_exact']} "
          f"keylen={rec['n_key']} ptlen={rec['n_pt']} keywords={rec['n_key_words']} "
          f"{rec['sec']:.0f}s", flush=True)
    print('  PT :', pt[:180], flush=True)
    print('  KEY:', key[:180], flush=True)
    json.dump(out, open('/home/user/infosecfollow/kryptos/results/xv5_repro.json', 'w'), indent=1)
print('DONE', flush=True)
