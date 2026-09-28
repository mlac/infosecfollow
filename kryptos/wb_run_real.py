"""Dual word-constrained beam: positive controls at 504 letters + real PK10/PK8/PK9."""
import sys, json, time, numpy as np; sys.path.insert(0,'.')
from lib import KA, CT, qscore
import wb_core as W
from wb_synth import make
alpha=KA; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha); BEAM=100000
tries={}
def T(m):
    if m not in tries:
        w,l=W.load_vocab(m,16); tries[m]=W.build_trie(w,l,alpha)
    return tries[m]
def idx(s): return np.array([ai[c] for c in s],dtype=np.int64)
out=[]
def run(tag,ctstr,kmin,mode,Wkey=2.0,truth=None):
    c=idx(ctstr)
    r=W.dual_beam(c,T(3),QGM,mode=mode,beam=BEAM,Wpt=1.0,Wkey=Wkey,trie_key=T(kmin))
    pt,key=W.decode_path(r['path'],c,mode,alpha)
    rec=dict(tag=tag,n=len(ctstr),kmin=kmin,mode=mode,Wkey=Wkey,beam=BEAM,
             obj=round(r['score'],4),qg=round(qscore(pt),4),sec=round(r['sec'],1),
             pt=pt,key=key)
    if truth:
        tp,tk=truth
        rec['pt_recovery']=round(sum(a==b for a,b in zip(pt,tp))/len(tp),4)
        rec['key_recovery']=round(sum(a==b for a,b in zip(key,tk))/len(tk),4)
    out.append(rec); json.dump(out,open('results/wb_dual_real.json','w'),indent=1)
    print(f"[{tag}] kmin={kmin} mode={mode} obj={rec['obj']:8.4f} qg={rec['qg']:7.4f} "
          f"rec={rec.get('pt_recovery','-')} {rec['sec']:.0f}s",flush=True)

# ---- positive controls at n=504, one per key-vocabulary setting
for kmin in (8,9,10):
    pt0,key0,ct0,_=make(seed=7,n=504,kminL=kmin)
    run(f'SYNTH504_k{kmin}',ct0,kmin,'add',truth=(pt0,key0))
# a second synthetic seed at the headline config
pt0,key0,ct0,_=make(seed=99,n=504,kminL=10)
run('SYNTH504_k10_s99',ct0,10,'add',truth=(pt0,key0))
# ---- real ciphertexts
for kmin in (10,9,8):
    for mode in ('add','sub','beau'):
        run('PK10',CT['pk10'],kmin,mode)
for tgt in ('pk8','pk9'):
    for mode in ('add','sub','beau'):
        run(tgt.upper(),CT[tgt],10,mode)
print('DONE',flush=True)
