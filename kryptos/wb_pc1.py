"""Positive control #1: dual beam on PK1 (192 letters, true key PROVENANCE, add on KA).
For each config we compare the beam's argmax objective against the TRUE solution's
objective under the identical objective.  If the truth is not the argmax, no beam
width can fix it -- the objective, not the search, is the failure."""
import sys, json, time, numpy as np; sys.path.insert(0,'.')
from lib import KA, CT, PT, qscore
import wb_core as W
alpha=KA; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha)
ct=np.array([ai[c] for c in CT['pk1']],dtype=np.int64)
truept=PT['pk1']; truekey=('PROVENANCE'*30)[:len(truept)]
tries={}
def T(minL):
    if minL not in tries:
        w,l=W.load_vocab(minL,16); tries[minL]=W.build_trie(w,l,alpha)
    return tries[minL]
BEAM=int(sys.argv[1]) if len(sys.argv)>1 else 20000
out=[]
for kmin in (3,6,8,10):
    for (Wpt,Wkey) in ((1.0,1.0),(1.0,2.0),(1.0,4.0)):
        tp=T(3); tk=T(kmin)
        o=W.objective(truept,truekey,tp,QGM,alpha,Wpt,Wkey,trie_key=tk)
        r=W.dual_beam(ct,tp,QGM,mode='add',beam=BEAM,Wpt=Wpt,Wkey=Wkey,trie_key=tk)
        pt,key=W.decode_path(r['path'],ct,'add',alpha)
        rec=dict(kmin=kmin,Wpt=Wpt,Wkey=Wkey,beam=BEAM,
                 true_obj=round(o['obj'],4),beam_obj=round(r['score'],4),
                 beam_qg=round(qscore(pt),4),true_qg=round(o['qg_per'],4),
                 truth_is_argmax=bool(o['obj']>=r['score']),
                 head_pt=pt[:60],head_key=key[:60],sec=round(r['sec'],1))
        out.append(rec)
        print(f"kmin={kmin:2d} Wkey={Wkey} true_obj={o['obj']:8.4f} beam_obj={r['score']:8.4f} "
              f"beam_qg={qscore(pt):7.4f} truth_wins={rec['truth_is_argmax']} {r['sec']:.0f}s",flush=True)
        print(f"    PT  {pt[:70]}")
        print(f"    KEY {key[:70]}",flush=True)
json.dump(out,open(f'results/wb_pc1_beam{BEAM}.json','w'),indent=1)
