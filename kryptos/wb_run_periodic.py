"""Variant 2: plaintext word-constrained (soft), key FREE and periodic, L=25..63.
Periods 2-24 are already Tier-2 dead; this covers the unexplored long-period band.
usage: wb_run_periodic.py real|null [nshuffle]"""
import sys, json, numpy as np; sys.path.insert(0,'.')
from lib import KA, CT, PT, qscore
import wb_core as W
alpha=KA; ai={c:i for i,c in enumerate(alpha)}
QGM=W.qg_matrix(alpha); BI,UNI=W.bigram_tables(alpha)
w,l=W.load_vocab(3,16); tp=W.build_trie(w,l,alpha)
BEAM=100000
LS=[25,27,28,30,32,35,36,40,42,45,48,50,54,56,60,63]
def idx(s): return np.array([ai[c] for c in s],dtype=np.int64)
what=sys.argv[1]
if what=='real':
    out=[]
    # positive control at the extreme period, same machinery
    import random
    pt0=(PT['pk6']+PT['pk7']+PT['pk3'])[:504]
    for Lp in (25,45,63):
        rng=random.Random(11); kv=[rng.randrange(26) for _ in range(Lp)]
        c=np.array([(ai[p]+kv[i%Lp])%26 for i,p in enumerate(pt0)],dtype=np.int64)
        r=W.periodic_beam2(c,tp,QGM,mode='add',L=Lp,beam=BEAM,BI=BI,UNI=UNI)
        pv=W.periodic_decode(c,r['key'],'add',Lp); pt=''.join(alpha[x] for x in pv)
        rec=sum(a==b for a,b in zip(pt,pt0))/504
        print(f"PC L={Lp} obj={r['score']:.4f} qg={qscore(pt):.4f} ptrec={rec:.3f} {r['sec']:.0f}s",flush=True)
        out.append(dict(tag=f'PC_L{Lp}',L=Lp,obj=round(r['score'],4),qg=round(qscore(pt),4),
                        pt_recovery=round(rec,4),sec=round(r['sec'],1)))
    for tgt in ('pk10','pk8','pk9'):
        c=idx(CT[tgt])
        for mode in ('add','sub','beau'):
            for Lp in LS:
                if Lp*2 > len(c): continue
                r=W.periodic_beam2(c,tp,QGM,mode=mode,L=Lp,beam=BEAM,BI=BI,UNI=UNI)
                pv=W.periodic_decode(c,r['key'],mode,Lp); pt=''.join(alpha[x] for x in pv)
                out.append(dict(tag=tgt.upper(),L=Lp,mode=mode,obj=round(r['score'],4),
                                qg=round(qscore(pt),4),key=''.join(alpha[int(x)] for x in r['key']),
                                pt=pt,sec=round(r['sec'],1)))
                json.dump(out,open('results/wb_periodic_real.json','w'),indent=1)
                print(f"{tgt} {mode} L={Lp:2d} obj={r['score']:8.4f} qg={qscore(pt):7.4f} {r['sec']:.0f}s",flush=True)
    print('DONE',flush=True)
else:
    NSH=int(sys.argv[2]); base=idx(CT['pk10']); out=[]
    for s in range(NSH):
        rng=np.random.default_rng(2000+s); c=base.copy(); rng.shuffle(c)
        best=None
        for Lp in LS:
            r=W.periodic_beam2(c,tp,QGM,mode='add',L=Lp,beam=BEAM,BI=BI,UNI=UNI)
            pv=W.periodic_decode(c,r['key'],'add',Lp); pt=''.join(alpha[x] for x in pv)
            rec=dict(L=Lp,obj=round(r['score'],4),qg=round(qscore(pt),4))
            if best is None or rec['obj']>best['obj']: best=rec
        best['shuffle']=s; out.append(best)
        json.dump(out,open('results/wb_periodic_null.json','w'),indent=1)
        print(f"null {s:2d} bestL={best['L']} obj={best['obj']:.4f} qg={best['qg']:.4f}",flush=True)
    o=np.array([x['obj'] for x in out]); q=np.array([x['qg'] for x in out])
    print(f"NULL periodic n={len(o)} obj mean={o.mean():.4f} sd={o.std():.4f} max={o.max():.4f}"
          f" | qg mean={q.mean():.4f} max={q.max():.4f}",flush=True)
