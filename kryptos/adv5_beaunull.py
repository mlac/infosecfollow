"""ADV5: MODE-MATCHED null. Identical dual beam, mode taken from argv, on the SAME
letter-shuffles of PK10 (seeds 1000+s) used by wb_run_null.py."""
import sys, json, numpy as np; sys.path.insert(0,'/home/user/infosecfollow/kryptos')
from lib import KA, CT, qscore
import wb_core as W
alpha=KA; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha); BEAM=100000
MODE=sys.argv[1]; KMIN=int(sys.argv[2]); NSH=int(sys.argv[3])
w,l=W.load_vocab(3,16); tp=W.build_trie(w,l,alpha)
w,l=W.load_vocab(KMIN,16); tk=W.build_trie(w,l,alpha)
base=np.array([ai[c] for c in CT['pk10']],dtype=np.int64)
out=[]; fn=f'results/adv5_null_{MODE}_k{KMIN}.json'
for s in range(NSH):
    rng=np.random.default_rng(1000+s)
    c=base.copy(); rng.shuffle(c)
    r=W.dual_beam(c,tp,QGM,mode=MODE,beam=BEAM,Wpt=1.0,Wkey=2.0,trie_key=tk)
    pt,key=W.decode_path(r['path'],c,MODE,alpha)
    out.append(dict(shuffle=s,kmin=KMIN,mode=MODE,obj=round(r['score'],4),
                    qg=round(qscore(pt),4),sec=round(r['sec'],1),pt=pt[:120],key=key[:120]))
    json.dump(out,open(fn,'w'),indent=1)
    o=np.array([x['obj'] for x in out])
    print(f"null {s:2d} {MODE} kmin={KMIN} obj={out[-1]['obj']:8.4f} qg={out[-1]['qg']:7.4f} "
          f"{out[-1]['sec']:.0f}s | running mean={o.mean():.4f} max={o.max():.4f}",flush=True)
print('DONE',flush=True)
