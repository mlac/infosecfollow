"""Matched null for the periodic-beam top cell on PK8 / PK9.
The real search took its max over 16 periods x 3 modes; here the null is taken at
the SINGLE cell where the real maximum occurred (L=63) over add and beau.  A
single-cell null is <= the grid-max null, so failing to beat it is conservative."""
import sys, json, numpy as np; sys.path.insert(0,'.')
from lib import KA, CT, qscore
import wb_core as W
alpha=KA; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha); BI,UNI=W.bigram_tables(alpha)
w,l=W.load_vocab(3,16); tp=W.build_trie(w,l,alpha)
out={}
for tgt in ('pk9','pk8'):
    base=np.array([ai[c] for c in CT[tgt]],dtype=np.int64)
    rows=[]
    for s in range(20):
        rng=np.random.default_rng(3000+s); c=base.copy(); rng.shuffle(c)
        best=None
        for mode in ('add','beau'):
            r=W.periodic_beam2(c,tp,QGM,mode=mode,L=63,beam=100000,BI=BI,UNI=UNI)
            pv=W.periodic_decode(c,r['key'],mode,63); pt=''.join(alpha[x] for x in pv)
            rec=dict(mode=mode,obj=round(r['score'],4),qg=round(qscore(pt),4))
            if best is None or rec['obj']>best['obj']: best=rec
        best['shuffle']=s; rows.append(best)
        print(f"{tgt} null {s:2d} {best['mode']:4s} obj={best['obj']:.4f} qg={best['qg']:.4f}",flush=True)
    o=np.array([x['obj'] for x in rows]); q=np.array([x['qg'] for x in rows])
    out[tgt]=dict(rows=rows,obj_mean=round(o.mean(),4),obj_sd=round(o.std(ddof=1),4),
                  obj_max=round(o.max(),4),qg_mean=round(q.mean(),4),qg_max=round(q.max(),4),L=63)
    json.dump(out,open('results/wb_periodic_null_p89.json','w'),indent=1)
    print(f"NULL {tgt} L=63 n=20 obj mean={o.mean():.4f} sd={o.std(ddof=1):.4f} max={o.max():.4f} | qg max={q.max():.4f}",flush=True)
print('DONE',flush=True)
