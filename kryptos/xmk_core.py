"""xmk_core: byte-identical re-implementation of the M-A single-word search from mk_single.py,
refactored so the SAME code can be pointed at (i) the real pk9, (ii) shuffles of it, and
(iii) real sibling ciphertexts truncated to the same length.  Nothing about the grid changes."""
import sys, time; sys.path.insert(0,'.')
import numpy as np
from lib import KA, AZ
import mk_lib as M
ALPH={'KA':KA,'AZ':AZ}
LMIN,LMAX=3,16
ROUND=[24,26,30,32,36,40,45,48]
CONFIGS=[(ta,ka,md) for ta in ('KA','AZ') for ka in ('KA','AZ') for md in ('sub','add')]
byl=M.load_words(LMIN,LMAX)
WM={ka:{L:M.wordmat(byl[L],ALPH[ka]) for L in byl} for ka in ('KA','AZ')}
WCAT={ka:{L:np.hstack([WM[ka][L],WM[ka][L][:,::-1]]) for L in byl} for ka in ('KA','AZ')}

def Lset(a):
    s=set(range(a+1,2*a))|set(ROUND)
    return sorted(x for x in s if x>a and x%a!=0 and x<=48)

def kavec(n,ka):
    ki={c:i for i,c in enumerate(ALPH[ka])}
    return np.array([ki[KA[i%26]] for i in range(n)],dtype=np.int16)

def constructions(a,n,ka):
    i=np.arange(n); m=(i%a)
    yield ('plain','W',m,None)
    yield ('self2W','W',np.stack([m,m]),None)
    yield ('revsum','W',np.stack([m,(a-1-m)]),None)
    yield ('catrev','C',(i%(2*a)),None)
    yield ('prog','W',np.stack([m,(i//a)%a]),None)
    yield ('progrev','W',np.stack([m,a-1-((i//a)%a)]),None)
    kv=kavec(n,ka)
    yield ('KArun','W',m,kv)
    yield ('KArunrev','W',m,kv[::-1].copy())
    yield ('AZrun','W',m,(i%26).astype(np.int16))
    for L in Lset(a):
        mm=(i%L)%a
        yield (f'trunc{L}','W',mm,None)
        yield (f'selftrunc{L}','W',np.stack([mm,mm]),None)
        yield (f'revtrunc{L}','W',np.stack([mm,a-1-mm]),None)

def search_one_ct(ct, configs=CONFIGS, want_cells=False):
    """returns (list of per-config-run maxima, n_cells_per_config_run, best record, optional all cell maxima)"""
    run_max=[]; best=None; cells=0; allcells=[]
    for (ta,ka,md) in configs:
        C=M.to_idx(ct,ALPH[ta]); n=len(C); allpos=np.arange(n)
        cm_best=-1.0; c=0
        for a in range(LMIN,LMAX+1):
            for (name,which,cmp_,off) in constructions(a,n,ka):
                Wv=WM[ka][a] if which=='W' else WCAT[ka][a]
                sc=M.score_parts(C,Wv,[(allpos,cmp_)],md,off); c+=1
                b=float(sc.max())
                if want_cells: allcells.append(b)
                if b>cm_best:
                    cm_best=b
                    rec={'cfg':f'{ta}/{ka}/{md}','ioc':round(b,5),'w':byl[a][int(sc.argmax())],
                         'a':a,'name':name}
        run_max.append(cm_best); cells=c
        if best is None or cm_best>best['ioc']: best=rec
    return run_max, cells, best, allcells
