import sys,time,numpy as np; sys.path.insert(0,'.')
from lib import KA, CT, qscore
import wb_core as W
from wb_synth import make
alpha=KA; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha)
w,l=W.load_vocab(3,16); tp=W.build_trie(w,l,alpha)
w,l=W.load_vocab(10,16); tk=W.build_trie(w,l,alpha)
pt0,key0,ct0,_=make()
c=np.array([ai[x] for x in ct0],dtype=np.int64)
r=W.dual_beam(c,tp,QGM,mode='add',beam=100000,Wpt=1.0,Wkey=2.0,trie_key=tk,verbose=1)
pt,key=W.decode_path(r['path'],c,'add',alpha)
print('obj',r['score'],'qg',qscore(pt),'sec',r['sec'])
print('PTrec',sum(a==b for a,b in zip(pt,pt0))/504,'KEYrec',sum(a==b for a,b in zip(key,key0))/504)
print('PT ',pt[:100]); print('TRU',pt0[:100]); print('KEY',key[:100]); print('TRK',key0[:100])
