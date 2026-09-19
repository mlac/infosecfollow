"""Length-matched dual-beam null for PK8 (150) and PK9 (144): shuffles of the
target's OWN letters, identical beam/vocab/weights, all three modes per shuffle."""
import sys, json, numpy as np; sys.path.insert(0,'.')
from lib import KA, CT, qscore
import wb_core as W
alpha=KA; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha); BEAM=100000
w,l=W.load_vocab(3,16); tp=W.build_trie(w,l,alpha)
w,l=W.load_vocab(10,16); tk=W.build_trie(w,l,alpha)
out={}
for tgt in ('pk9','pk8'):
    base=np.array([ai[c] for c in CT[tgt]],dtype=np.int64); rows=[]
    for s in range(20):
        rng=np.random.default_rng(4000+s); c=base.copy(); rng.shuffle(c)
        best=None
        for mode in ('add','sub','beau'):
            r=W.dual_beam(c,tp,QGM,mode=mode,beam=BEAM,Wpt=1.0,Wkey=2.0,trie_key=tk)
            pt,_=W.decode_path(r['path'],c,mode,alpha)
            rec=dict(mode=mode,obj=round(r['score'],4),qg=round(qscore(pt),4))
            if best is None or rec['obj']>best['obj']: best=rec
        best['shuffle']=s; rows.append(best)
        print(f"{tgt} null {s:2d} {best['mode']:4s} obj={best['obj']:.4f} qg={best['qg']:.4f}",flush=True)
    o=np.array([x['obj'] for x in rows]); q=np.array([x['qg'] for x in rows])
    out[tgt]=dict(rows=rows,n=len(rows),obj_mean=round(o.mean(),4),obj_sd=round(o.std(ddof=1),4),
                  obj_max=round(o.max(),4),qg_mean=round(q.mean(),4),qg_sd=round(q.std(ddof=1),4),
                  qg_max=round(q.max(),4))
    json.dump(out,open('results/wb_dual_null_p89.json','w'),indent=1)
    print(f"NULL {tgt} n=20 obj mean={o.mean():.4f} sd={o.std(ddof=1):.4f} max={o.max():.4f} | qg max={q.max():.4f}",flush=True)
print('DONE',flush=True)
