"""XV5 - independently re-run ONE published null replicate (seed 1000, mode add,
kmin=8) to confirm the published null artifact is genuine and reproducible."""
import sys, json, numpy as np; sys.path.insert(0,'/home/user/infosecfollow/kryptos')
from lib import KA, CT, qscore
import wb_core as W
alpha=KA; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha)
w,l=W.load_vocab(3,16); tp=W.build_trie(w,l,alpha)
w,l=W.load_vocab(8,16); tk=W.build_trie(w,l,alpha)
base=np.array([ai[c] for c in CT['pk10']],dtype=np.int64)
rng=np.random.default_rng(1000); c=base.copy(); rng.shuffle(c)
r=W.dual_beam(c,tp,QGM,mode='add',beam=100000,Wpt=1.0,Wkey=2.0,trie_key=tk)
pt,key=W.decode_path(r['path'],c,'add',alpha)
pub=json.load(open('/home/user/infosecfollow/kryptos/results/wb_dual_null_k8.json'))[0]
print('re-run  obj=%.4f qg=%.4f'%(r['score'],qscore(pt)))
print('published obj=%.4f qg=%.4f'%(pub['obj'],pub['qg']))
print('MATCH:', abs(r['score']-pub['obj'])<1e-4 and pt[:200]==pub['pt'])
json.dump(dict(rerun_obj=round(r['score'],4),published_obj=pub['obj'],
               match=bool(abs(r['score']-pub['obj'])<1e-4 and pt[:200]==pub['pt'])),
          open('/home/user/infosecfollow/kryptos/results/xv5_checkpub.json','w'),indent=1)
