"""MATCHED NULL: the identical dual beam on letter-shuffled PK10."""
import sys, json, numpy as np; sys.path.insert(0,'.')
from lib import KA, CT, qscore
import wb_core as W
alpha=KA; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha); BEAM=100000
KMIN=int(sys.argv[1]); NSH=int(sys.argv[2])
w,l=W.load_vocab(3,16); tp=W.build_trie(w,l,alpha)
w,l=W.load_vocab(KMIN,16); tk=W.build_trie(w,l,alpha)
base=np.array([ai[c] for c in CT['pk10']],dtype=np.int64)
out=[]
for s in range(NSH):
    rng=np.random.default_rng(1000+s)
    c=base.copy(); rng.shuffle(c)
    r=W.dual_beam(c,tp,QGM,mode='add',beam=BEAM,Wpt=1.0,Wkey=2.0,trie_key=tk)
    pt,key=W.decode_path(r['path'],c,'add',alpha)
    out.append(dict(shuffle=s,kmin=KMIN,obj=round(r['score'],4),qg=round(qscore(pt),4),
                    sec=round(r['sec'],1),pt=pt[:200],key=key[:200]))
    json.dump(out,open(f'results/wb_dual_null_k{KMIN}.json','w'),indent=1)
    print(f"null {s:2d} kmin={KMIN} obj={out[-1]['obj']:8.4f} qg={out[-1]['qg']:7.4f} {out[-1]['sec']:.0f}s",flush=True)
o=np.array([x['obj'] for x in out]); q=np.array([x['qg'] for x in out])
print(f"NULL kmin={KMIN} n={len(o)} obj mean={o.mean():.4f} sd={o.std():.4f} max={o.max():.4f} | qg mean={q.mean():.4f} max={q.max():.4f}",flush=True)
