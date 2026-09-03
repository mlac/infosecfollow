"""Where does the dual beam lose power?  Same synthetic construction at n=504
with the key built from words of length >= kminL, searched with the matching
key vocabulary.  Recovery fraction maps the boundary of the attack's reach."""
import sys, json, numpy as np; sys.path.insert(0,'.')
from lib import KA, CT, qscore
import wb_core as W
from wb_synth import make
alpha=KA; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha); BEAM=100000
w,l=W.load_vocab(3,16); tp=W.build_trie(w,l,alpha)
out=[]
for kmin in (5,6,7):
    w,l=W.load_vocab(kmin,16); tk=W.build_trie(w,l,alpha)
    pt0,key0,ct0,_=make(seed=7,n=504,kminL=kmin)
    c=np.array([ai[x] for x in ct0],dtype=np.int64)
    r=W.dual_beam(c,tp,QGM,mode='add',beam=BEAM,Wpt=1.0,Wkey=2.0,trie_key=tk)
    pt,key=W.decode_path(r['path'],c,'add',alpha)
    rec=sum(a==b for a,b in zip(pt,pt0))/504
    out.append(dict(tag=f'SYNTH504_k{kmin}',kmin=kmin,obj=round(r['score'],4),
                    qg=round(qscore(pt),4),pt_recovery=round(rec,4),sec=round(r['sec'],1)))
    print(f"SYNTH k{kmin} obj={r['score']:.4f} rec={rec:.3f} {r['sec']:.0f}s",flush=True)
    cc=np.array([ai[x] for x in CT['pk10']],dtype=np.int64)
    r2=W.dual_beam(cc,tp,QGM,mode='add',beam=BEAM,Wpt=1.0,Wkey=2.0,trie_key=tk)
    pt2,key2=W.decode_path(r2['path'],cc,'add',alpha)
    out.append(dict(tag='PK10',kmin=kmin,mode='add',obj=round(r2['score'],4),
                    qg=round(qscore(pt2),4),sec=round(r2['sec'],1),pt=pt2,key=key2))
    print(f"PK10   k{kmin} obj={r2['score']:.4f} qg={qscore(pt2):.4f} {r2['sec']:.0f}s",flush=True)
    json.dump(out,open('results/wb_dual_power.json','w'),indent=1)
print('DONE',flush=True)
