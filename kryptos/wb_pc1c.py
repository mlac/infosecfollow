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
BEAM=100000
out=[]
for kmin in (9,10):
  for Wkey in (1.0,2.0,3.0):
    tp=T(3); tk=T(kmin)
    o=W.objective(truept,truekey,tp,QGM,alpha,1.0,Wkey,trie_key=tk)
    r=W.dual_beam(ct,tp,QGM,mode='add',beam=BEAM,Wpt=1.0,Wkey=Wkey,trie_key=tk)
    pt,key=W.decode_path(r['path'],ct,'add',alpha)
    rp=sum(a==b for a,b in zip(pt,truept))/len(truept)
    rk=sum(a==b for a,b in zip(key,truekey))/len(truekey)
    print(f"kmin={kmin} Wkey={Wkey} true_obj={o['obj']:.4f} beam_obj={r['score']:.4f} "
          f"truth_wins={o['obj']>=r['score']} PTrec={rp:.3f} KEYrec={rk:.3f} {r['sec']:.0f}s",flush=True)
    print('   PT ',pt[:96]); print('   KEY',key[:96],flush=True)
    out.append(dict(kmin=kmin,Wkey=Wkey,beam=BEAM,true_obj=round(o['obj'],4),
       beam_obj=round(r['score'],4),truth_wins=bool(o['obj']>=r['score']),
       pt_recovery=round(rp,4),key_recovery=round(rk,4),pt=pt,key=key,
       beam_qg=round(qscore(pt),4),sec=round(r['sec'],1)))
json.dump(out,open('results/wb_pc1_beam100000.json','w'),indent=1)
