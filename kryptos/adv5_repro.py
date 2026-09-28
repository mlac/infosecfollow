"""ADV5: exact reproduction of the flagged PK10 dual-beam cells."""
import sys, json, time, numpy as np; sys.path.insert(0,'/home/user/infosecfollow/kryptos')
from lib import KA, CT, qscore
import wb_core as W
alpha=KA; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha); BEAM=100000
w,l=W.load_vocab(3,16); tp=W.build_trie(w,l,alpha)
print('pt vocab len>=3 words =',len(w),flush=True)
w8,l8=W.load_vocab(8,16); t8=W.build_trie(w8,l8,alpha)
print('key vocab len>=8 words =',len(w8),flush=True)
c=np.array([ai[ch] for ch in CT['pk10']],dtype=np.int64)
out=[]
for mode,claimed in (('beau',-6.4241),('add',-6.4826)):
    t0=time.time()
    r=W.dual_beam(c,tp,QGM,mode=mode,beam=BEAM,Wpt=1.0,Wkey=2.0,trie_key=t8)
    pt,key=W.decode_path(r['path'],c,mode,alpha)
    obj=round(r['score'],4)
    # round-trip re-encrypt
    pv=np.array([ai[x] for x in pt]); kv=np.array([ai[x] for x in key])
    if mode=='add': cc=(pv+kv)%26
    elif mode=='sub': cc=(pv-kv)%26
    else: cc=(kv-pv)%26
    ctre=''.join(alpha[int(x)] for x in cc)
    rt = (ctre==CT['pk10'])
    print(f"{mode}: obj={obj} claimed={claimed} match={obj==claimed} qg={qscore(pt):.4f} roundtrip={rt} {time.time()-t0:.0f}s",flush=True)
    print('  PT:',pt[:120],flush=True)
    print('  KY:',key[:120],flush=True)
    out.append(dict(mode=mode,obj=obj,claimed=claimed,exact=obj==claimed,qg=round(qscore(pt),4),
                    roundtrip=bool(rt),pt=pt,key=key,sec=round(time.time()-t0,1)))
    json.dump(out,open('results/adv5_repro.json','w'),indent=1)
