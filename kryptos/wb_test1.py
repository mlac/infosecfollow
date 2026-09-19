import sys, time, numpy as np; sys.path.insert(0,'.')
from lib import KA, AZ, CT, PT, qscore, ka_to_az
import wb_core as W

alpha = KA
t0=time.time()
words, lp = W.load_vocab(3,16)
print('vocab', len(words), 'lp range', lp.min(), lp.max(), f'{time.time()-t0:.1f}s', flush=True)
t0=time.time()
trie = W.build_trie(words, lp, alpha)
print('trie nodes', trie[3], f'{time.time()-t0:.1f}s', flush=True)
QGM = W.qg_matrix(alpha)
ai={c:i for i,c in enumerate(alpha)}
ct = np.array([ai[c] for c in CT['pk1']], dtype=np.int64)
for beam in (2000, 20000):
    r = W.dual_beam(ct, trie, QGM, mode='add', beam=beam, Wpt=1.0, Wkey=1.0, verbose=0)
    pt, key = W.decode_path(r['path'], ct, 'add', alpha)
    print(f"beam={beam} obj={r['score']:.4f} qg={qscore(ka_to_az(pt)):.4f} {r['sec']:.1f}s")
    print('  PT ', pt[:100])
    print('  KEY', key[:100])
    print('  TRUE PT ', PT['pk1'][:100])
