"""Dual beam with the plain A-Z alphabet instead of the Kryptos alphabet.
(For a letter-shuffled ciphertext the alphabet is only a relabelling, so the
KA matched null applies unchanged.)"""
import sys, json, numpy as np; sys.path.insert(0,'.')
from lib import AZ, CT, qscore
import wb_core as W
from wb_synth import make
alpha=AZ; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha); BEAM=100000
w,l=W.load_vocab(3,16); tp=W.build_trie(w,l,alpha)
tk={}
for m in (10,8):
    w,l=W.load_vocab(m,16); tk[m]=W.build_trie(w,l,alpha)
out=[]
def run(tag,s,kmin,mode):
    c=np.array([ai[x] for x in s],dtype=np.int64)
    r=W.dual_beam(c,tp,QGM,mode=mode,beam=BEAM,Wpt=1.0,Wkey=2.0,trie_key=tk[kmin])
    pt,key=W.decode_path(r['path'],c,mode,alpha)
    out.append(dict(tag=tag,alpha='AZ',kmin=kmin,mode=mode,obj=round(r['score'],4),
                    qg=round(qscore(pt),4),sec=round(r['sec'],1),pt=pt,key=key))
    json.dump(out,open('results/wb_dual_az.json','w'),indent=1)
    print(f"[AZ {tag}] kmin={kmin} {mode} obj={r['score']:8.4f} qg={qscore(pt):7.4f} {r['sec']:.0f}s",flush=True)
for kmin in (10,8):
    for mode in ('add','sub','beau'):
        run('PK10',CT['pk10'],kmin,mode)
print('DONE',flush=True)
