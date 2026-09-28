"""xmk: adversarial verification of the manufactured-long-key (M-A/M-B/M-C/M-D/M-E) claim.
Stage 1 -- exact reproduction of the headline configurations from artifacts on disk."""
import sys, json, collections; sys.path.insert(0,'.')
import numpy as np
from lib import KA, AZ, CT, ka_to_az, qscore, ioc
import mk_lib as M
ALPH={'KA':KA,'AZ':AZ}
byl=M.load_words(3,16)
out={}

def single_key(n,a,L,name,ka):
    i=np.arange(n); mm=(i%L)%a if L else (i%a)
    if name.startswith('revtrunc'): return np.stack([mm,a-1-mm])
    if name.startswith('selftrunc'): return np.stack([mm,mm])
    if name.startswith('trunc'): return mm
    raise ValueError(name)

def decrypt_single(tgt,ta,ka,md,w,a,name,L):
    C=M.to_idx(CT[tgt],ALPH[ta]); n=len(C)
    ki={c:i for i,c in enumerate(ALPH[ka])}
    wv=np.array([ki[c] for c in w])
    cm=single_key(n,a,L,name,ka)
    if cm.ndim==1: S=wv[cm]%26
    else: S=(wv[cm[0]]+wv[cm[1]])%26
    R=(C-S)%26 if md=='sub' else ((C+S)%26 if md=='add' else (S-C)%26)
    pt=''.join(ALPH[ta][int(v)] for v in R)
    az=pt if ta=='AZ' else ka_to_az(pt)
    return R,pt,az,S

# ---- headline M-A hit: pk9 KA/AZ/sub revtrunc14 METALHEAD a=9 ioc 0.06313 z 8.1
R,pt,az,S=decrypt_single('pk9','KA','AZ','sub','METALHEAD',9,'revtrunc14',14)
cnt=collections.Counter(pt)
out['MA_headline']={'claimed_ioc':0.06313,'recomputed_ioc':round(float(ioc(R)),5),
  'plaintext':pt,'quadgram_per_letter':round(qscore(az),3),
  'top4_letters':cnt.most_common(4),'n':len(pt),
  'distinct_keystream_symbols':int(len(set(S.tolist()))),
  'keystream_period':14,'keystream_first28':S[:28].tolist(),
  'key_len_chars':9}

# how many DISTINCT keystreams does the whole revtrunc(a=9,L=14) cell really have?
ki={c:i for i,c in enumerate(AZ)}
W=M.wordmat(byl[9],AZ)
Vs=(W[:,np.arange(9)]+W[:,8-np.arange(9)])%26          # v(j)=W[j]+W[8-j], j=0..8, v(j)=v(8-j)
red=Vs[:,:5]                                            # only j=0..4 are independent
uniq=np.unique(red,axis=0)
out['MA_headline']['words_len9']=int(W.shape[0])
out['MA_headline']['distinct_effective_keys_in_cell']=int(uniq.shape[0])
out['MA_headline']['note_symmetry']='S[i]=W[j]+W[a-1-j] is palindromic in j, so a 9-letter word contributes only 5 free symbols'

# ---- re-derive the in-cell z the pipeline reported (z=8.1)
C=M.to_idx(CT['pk9'],KA); n=len(C); allpos=np.arange(n)
cm=single_key(n,9,14,'revtrunc14','AZ')
sc=M.score_parts(C,W,[(allpos,cm)],'sub',None)
b,mu,sd,z=M.zstat(sc)
out['MA_headline']['in_cell_recomputed']={'max':round(float(b),5),'mean':round(float(mu),5),
  'sd':round(float(sd),5),'z':round(float(z),2),'argmax_word':byl[9][int(sc.argmax())],
  'n_words_in_cell':int(len(sc))}

# ---- M-B1 headline pk8 joint 0.06656 (BENAIAH/BLOODING a=7 b=8 L=28) reproduce
def decrypt_two(t,ta,ka,md,a,b,Lk,wA,wB):
    ct=CT[t]; C=M.to_idx(ct,ALPH[ta]); n=len(C)
    ki={c:i for i,c in enumerate(ALPH[ka])}
    S=(np.array([ki[c] for c in wA])[M.map_mod(n,Lk,a)]+
       np.array([ki[c] for c in wB])[M.map_mod(n,Lk,b)])%26
    R=(C-S)%26 if md=='sub' else ((C+S)%26 if md=='add' else (S-C)%26)
    pt=''.join(ALPH[ta][int(v)] for v in R)
    az=pt if ta=='AZ' else ka_to_az(pt)
    c=collections.Counter(pt)
    return {'ioc':round(float(ioc(R)),5),'quadgram_per_letter':round(qscore(az),3),
            'top4':c.most_common(4),'plaintext':pt}
out['MB1_headline_pk8']=decrypt_two('pk8','KA','AZ','sub',7,8,28,'BENAIAH','BLOODING')
out['MB1_headline_pk8']['claimed_ioc']=0.06656
out['MB1_headline_pk9']=decrypt_two('pk9','AZ','AZ','sub',7,6,14,'CARALHO','CECCHI')
out['MB1_headline_pk9']['claimed_ioc']=0.06614

# ---- calibration: what does IoC 0.063 mean at n=144?
rng=np.random.default_rng(1)
eng=[]
txt=''.join(PT for PT in [__import__('lib').PT[k] for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7']])
for _ in range(4000):
    s=rng.integers(0,len(txt)-144); seg=txt[s:s+144]
    eng.append(ioc(M.to_idx(seg,AZ)))
eng=np.array(eng)
out['english_n144']={'mean':round(float(eng.mean()),5),'p5':round(float(np.percentile(eng,5)),5),
  'p50':round(float(np.percentile(eng,50)),5),'p95':round(float(np.percentile(eng,95)),5),
  'frac_below_0.06313':round(float((eng<0.06313).mean()),4)}
json.dump(out,open('results/xmk_repro.json','w'),indent=1)
print(json.dumps(out,indent=1)[:4000])
