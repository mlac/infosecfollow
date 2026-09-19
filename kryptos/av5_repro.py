"""ADVERSARIAL VERIFY: reproduce the claimed best cell exactly, then audit it.
Claimed: PK10, KA, key vocab len>=8, mode 'beau', beam 100000, Wpt=1.0 Wkey=2.0
         -> obj = -6.4241 / letter, quadgram = -4.1858
"""
import sys, json, numpy as np; sys.path.insert(0,'.')
from lib import KA, CT, qscore
import wb_core as W
alpha=KA; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha); BEAM=100000
w,l=W.load_vocab(3,16); tp=W.build_trie(w,l,alpha)
w,l=W.load_vocab(8,16); tk=W.build_trie(w,l,alpha)
ct=CT['pk10']; c=np.array([ai[x] for x in ct],dtype=np.int64)
r=W.dual_beam(c,tp,QGM,mode='beau',beam=BEAM,Wpt=1.0,Wkey=2.0,trie_key=tk)
pt,key=W.decode_path(r['path'],c,'beau',alpha)
obj=round(r['score'],4); qg=round(qscore(pt),4)
print('REPRO obj=',obj,' claimed -6.4241   qg=',qg,' claimed -4.1858',flush=True)

# --- round trip: re-encrypt pt under key in beau mode -> must equal PK10
pv=np.array([ai[x] for x in pt]); kv=np.array([ai[x] for x in key])
ctv=(kv-pv)%26
ct2=''.join(alpha[int(x)] for x in ctv)
print('ROUNDTRIP exact:', ct2==ct, flush=True)

# --- segmentations
lpt,segp=W.best_seg_lp(pt,tp,alpha)
lky,segk=W.best_seg_lp(key,tk,alpha,tail=True)
print('n_pt=',len(pt),'n_key=',len(key),'key_words=',len(segk) if segk else None)
print('PT :',pt)
print('KEY:',key)
print('PT SEG :',' '.join(segp) if segp else None)
print('KEY SEG:',' '.join(segk) if segk else None)
json.dump(dict(obj=obj,qg=qg,claimed_obj=-6.4241,claimed_qg=-4.1858,
               reproduces=(obj==-6.4241 and qg==-4.1858),
               roundtrip_exact=bool(ct2==ct),n_pt=len(pt),n_key=len(key),
               pt=pt,key=key,pt_seg=segp,key_seg=segk),
          open('results/av5_repro.json','w'),indent=1)
print('DONE',flush=True)
