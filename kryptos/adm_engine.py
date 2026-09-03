"""Independent re-implementation of the M-A single-word manufactured-key search.
Written from the construction spec, not copied from mk_lib. Used for both the real run
and the matched nulls, byte-identical code path for both.
"""
import sys; sys.path.insert(0,'.')
import numpy as np

KA = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
AZ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALPH = {'KA':KA,'AZ':AZ}
LMIN, LMAX = 3, 16
ROUND = [24,26,30,32,36,40,45,48]
CONFIGS = [(ta,ka,md) for ta in ('KA','AZ') for ka in ('KA','AZ') for md in ('sub','add')]

def load_words(path='words.txt'):
    byl={}
    for w in open(path).read().split():
        L=len(w)
        if LMIN<=L<=LMAX: byl.setdefault(L,[]).append(w)
    return byl

def wordmat(words, al):
    d={c:i for i,c in enumerate(al)}
    return np.array([[d[c] for c in w] for w in words], dtype=np.int16)

def to_idx(s, al):
    d={c:i for i,c in enumerate(al)}
    return np.array([d[c] for c in s], dtype=np.int16)

def ioc_rows(R):
    R=np.asarray(R,dtype=np.int64); N,L=R.shape
    off=(np.arange(N,dtype=np.int64)*26)[:,None]
    cnt=np.bincount((off+R).ravel(),minlength=N*26).reshape(N,26).astype(np.float64)
    return (cnt*(cnt-1)).sum(1)/(L*(L-1))

def Lset(a):
    s=set(range(a+1,2*a))|set(ROUND)
    return sorted(x for x in s if x>a and x%a!=0 and x<=48)

def kavec(n, ka):
    d={c:i for i,c in enumerate(ALPH[ka])}
    return np.array([d[KA[i%26]] for i in range(n)],dtype=np.int16)

def constructions(a,n,ka):
    i=np.arange(n); m=i%a
    yield ('plain','W',m,None)
    yield ('self2W','W',np.stack([m,m]),None)
    yield ('revsum','W',np.stack([m,a-1-m]),None)
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

def cell_scores(C, Wv, cm, md, off, chunk=6000):
    """IoC of the full decrypt for every word row. Returns (N,) float."""
    N=Wv.shape[0]
    Cb=C.astype(np.int16)
    if off is not None: Cb=((Cb-off.astype(np.int16))%26).astype(np.int16)
    Cb=Cb[None,:]
    cm=np.asarray(cm,dtype=np.int64)
    out=np.empty(N)
    for s in range(0,N,chunk):
        Wc=Wv[s:s+chunk]
        if cm.ndim==1: W=Wc[:,cm]
        else:
            W=Wc[:,cm[0]].astype(np.int32)
            for row in cm[1:]: W=W+Wc[:,row]
            W=(W%26).astype(np.int16)
        if md=='sub': R=(Cb-W)%26
        elif md=='add': R=(Cb+W)%26
        else: R=(W-Cb)%26
        out[s:s+chunk]=ioc_rows(R)
    return out

class Engine:
    def __init__(self, byl=None):
        self.byl = byl if byl is not None else load_words()
        self.WM={ka:{L:wordmat(self.byl[L],ALPH[ka]) for L in self.byl} for ka in ('KA','AZ')}
        self.WCAT={ka:{L:np.hstack([self.WM[ka][L],self.WM[ka][L][:,::-1]]) for L in self.byl}
                   for ka in ('KA','AZ')}

    def run(self, ct, configs=None, keep_cells=False):
        """Full M-A search on one ciphertext. Returns dict with grid max + argmax + all cell maxima."""
        configs = configs or CONFIGS
        n=len(ct)
        best=(-1.0,None); cells=[]
        ncells=0; nhyp=0
        for (ta,ka,md) in configs:
            C=to_idx(ct,ALPH[ta])
            for a in range(LMIN,LMAX+1):
                if a not in self.byl: continue
                for (name,which,cm,off) in constructions(a,n,ka):
                    Wv=self.WM[ka][a] if which=='W' else self.WCAT[ka][a]
                    sc=cell_scores(C,Wv,cm,md,off)
                    ncells+=1; nhyp+=sc.shape[0]
                    j=int(sc.argmax()); b=float(sc[j])
                    if keep_cells:
                        cells.append((round(b,6),f'{ta}/{ka}/{md}',name,a,
                                      float(sc.mean()),float(sc.std())))
                    if b>best[0]:
                        best=(b,{'cfg':f'{ta}/{ka}/{md}','name':name,'a':a,
                                 'w':self.byl[a][j],'ioc':round(b,5),
                                 'in_cell_mean':round(float(sc.mean()),5),
                                 'in_cell_sd':round(float(sc.std()),5),
                                 'in_cell_z':round((b-float(sc.mean()))/float(sc.std()),2)})
        return {'grid_max':round(best[0],5),'argmax':best[1],
                'n_cells':ncells,'n_hypotheses':nhyp,'cells':cells}

def shuffled(ct, rng):
    a=np.frombuffer(ct.encode(),dtype=np.uint8).copy(); rng.shuffle(a)
    return a.tobytes().decode()
