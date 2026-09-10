import sys, json, numpy as np; sys.path.insert(0,'.')
from lib import KA, CT, PT, qscore
import wb_core as W
alpha=KA; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha)
ct=np.array([ai[c] for c in CT['pk1']],dtype=np.int64)
truept=PT['pk1']; truekey=('PROVENANCE'*30)[:len(truept)]
tries={}
def T(m):
    if m not in tries:
        w,l=W.load_vocab(m,16); tries[m]=W.build_trie(w,l,alpha)
    return tries[m]
BEAM=int(sys.argv[1])
out=[]
for kmin in (7,8,9,10,12):
  for (Wpt,Wkey) in ((1.0,1.0),(1.0,2.0)):
    tp=T(3); tk=T(kmin)
    o=W.objective(truept,truekey,tp,QGM,alpha,Wpt,Wkey,trie_key=tk)
    r=W.dual_beam(ct,tp,QGM,mode='add',beam=BEAM,Wpt=Wpt,Wkey=Wkey,trie_key=tk)
    pt,key=W.decode_path(r['path'],ct,'add',alpha)
    rec_pt=sum(a==b for a,b in zip(pt,truept))/len(truept)
    rec_ky=sum(a==b for a,b in zip(key,truekey))/len(truekey)
    rec=dict(kmin=kmin,Wpt=Wpt,Wkey=Wkey,beam=BEAM,true_obj=round(o['obj'],4),
             beam_obj=round(r['score'],4),beam_qg=round(qscore(pt),4),
             truth_wins=bool(o['obj']>=r['score']),pt_recovery=round(rec_pt,4),
             key_recovery=round(rec_ky,4),pt=pt,key=key,sec=round(r['sec'],1))
    out.append(rec)
    print(f"kmin={kmin:2d} Wkey={Wkey} true_obj={o['obj']:8.4f} beam_obj={r['score']:8.4f} "
          f"truth_wins={rec['truth_wins']!s:5s} PTrec={rec_pt:.3f} KEYrec={rec_ky:.3f} {r['sec']:.0f}s",flush=True)
json.dump(out,open(f'results/wb_pc1_beam{BEAM}.json','w'),indent=1)
