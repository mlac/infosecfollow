import sys,numpy as np,random; sys.path.insert(0,'.')
from lib import KA, PT, qscore
import wb_core as W
alpha=KA; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha)
w,l=W.load_vocab(3,16); tp=W.build_trie(w,l,alpha)
pt0=(PT['pk6']+PT['pk7']+PT['pk3'])[:504]
for L in (27,45):
  rng=random.Random(5); keyv=[rng.randrange(26) for _ in range(L)]
  c=np.array([(ai[p]+keyv[i%L])%26 for i,p in enumerate(pt0)],dtype=np.int64)
  for beam in (100000,400000):
    r=W.periodic_beam(c,tp,QGM,mode='add',L=L,beam=beam,Wpt=1.0)
    if r['score'] is None:
        print(f'L={L} beam={beam} DEAD at {r["dead_at"]} {r["sec"]:.0f}s',flush=True); continue
    pv=W.periodic_decode(c,r['key'],'add',L); pt=''.join(alpha[x] for x in pv)
    rec=sum(a==b for a,b in zip(pt,pt0))/504
    print(f'L={L} beam={beam} obj={r["score"]:.4f} qg={qscore(pt):.4f} rec={rec:.3f} surv={r["survivors"]} {r["sec"]:.0f}s',flush=True)
    print('   ',pt[:80],flush=True)
