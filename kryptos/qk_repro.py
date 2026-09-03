"""ADVERSARIAL REPRO of the manufactured-key concat/interleave claimed hit.
Claim: pk9, cfg KA/KA/add, kind D (interleave), a=10,b=7 -> joint IoC 0.06799
       wA=GABRIELSEN wB=DENHOLM  (mk_cat_real.json, above shuffle-null D max 0.06391)
Also re-runs the kind-C claimed hit (pk9 KA/AZ/sub 6,8 APIECE|SPAINISH 0.06770).
Re-implements the cell independently from mk_cat.py's layout() to check it, then
autopsies the decrypt and does an explicit round-trip.
"""
import sys, json, time; sys.path.insert(0,'.')
import numpy as np
from lib import KA, AZ, CT, ioc, qscore
import mk_lib as M
from collections import Counter

ALPH={'KA':KA,'AZ':AZ}
byl=M.load_words(3,12)
K=200

def cell(ct, ta, ka, md, kind, a, b, K=200):
    """independent re-implementation of one (kind,a,b) cell of mk_cat.py"""
    C=M.to_idx(ct,ALPH[ta]); n=len(C)
    i=np.arange(n)
    if kind in ('C','CR'):
        P=a+b; r=i%P
        posA=np.nonzero(r<a)[0]; posB=np.nonzero(r>=a)[0]
        cmA=r[posA]; cmB=r[posB]-a
    else:
        posA=np.nonzero(i%2==0)[0]; posB=np.nonzero(i%2==1)[0]
        cmA=(posA//2)%a; cmB=(posB//2)%b
    WA=M.wordmat(byl[a],ALPH[ka])
    WB=M.wordmat(byl[b],ALPH[ka])
    if kind=='CR': WB=WB[:,::-1].copy()
    sA=M.score_parts(C,WA,[(posA,cmA)],md)
    sB=M.score_parts(C,WB,[(posB,cmB)],md)
    _,_,_,zA=M.zstat(sA); _,_,_,zB=M.zstat(sB)
    iA=np.argsort(-sA)[:K]; iB=np.argsort(-sB)[:K]
    best=-1; bx=by=0
    fA=np.zeros(n,dtype=np.int64); fA[posA]=cmA
    fB=np.zeros(n,dtype=np.int64); fB[posB]=cmB
    for x in range(len(iA)):
        SA=np.zeros(n,dtype=np.int16); SA[posA]=WA[iA[x]][cmA]
        SB=np.zeros((len(iB),n),dtype=np.int16); SB[:,posB]=WB[iB][:,cmB]
        base=C.astype(np.int16)
        if md=='sub': R=(base[None,:]-SA[None,:]-SB)%26
        elif md=='add': R=(base[None,:]+SA[None,:]+SB)%26
        else: R=(SA[None,:]+SB-base[None,:])%26
        v=M.ioc_rows_fast(R); j=int(v.argmax())
        if v[j]>best: best,bx,by=float(v[j]),x,j
    wA=byl[a][int(iA[bx])]; wB=byl[b][int(iB[by])]
    # rebuild decrypt for the winner
    SA=np.zeros(n,dtype=np.int16); SA[posA]=WA[iA[bx]][cmA]
    SB=np.zeros(n,dtype=np.int16); SB[posB]=WB[iB[by]][cmB]
    S=(SA+SB)%26
    base=C.astype(np.int16)
    if md=='sub': R=(base-S)%26
    elif md=='add': R=(base+S)%26
    else: R=(S-base)%26
    pt=''.join(ALPH[ta][x] for x in R)
    # ROUND TRIP: re-encrypt pt with the same keystream -> must give ct back
    Rr=M.to_idx(pt,ALPH[ta])
    if md=='sub': Cr=(Rr+S)%26
    elif md=='add': Cr=(Rr-S)%26
    else: Cr=(S-Rr)%26
    ctr=''.join(ALPH[ta][x] for x in Cr)
    return dict(kind=kind,a=a,b=b,cfg=f'{ta}/{ka}/{md}',zA=round(float(zA),3),zB=round(float(zB),3),
                joint=round(best,5),wA=wA,wB=wB,pt=pt,roundtrip=(ctr==ct),
                ioc_check=round(ioc(pt),5))

out={}
CLAIMS=[('pk9','KA','KA','add','D',10,7,0.06799,'GABRIELSEN','DENHOLM'),
        ('pk9','KA','AZ','sub','C',6,8,0.06770,'APIECE','SPAINISH'),
        ('pk9','KA','AZ','sub','CR',6,8,0.06750,'LATOUR','SETALVAD')]
for (t,ta,ka,md,kind,a,b,claimed,cwA,cwB) in CLAIMS:
    t0=time.time()
    r=cell(CT[t],ta,ka,md,kind,a,b)
    r['target']=t; r['claimed_joint']=claimed; r['claimed_wA']=cwA; r['claimed_wB']=cwB
    r['reproduces']=abs(r['joint']-claimed)<1e-5 and r['wA']==cwA and r['wB']==cwB
    c=Counter(r['pt']); tot=len(r['pt'])
    r['top5_letters']=[(ch,k,round(100*k/tot,1)) for ch,k in c.most_common(5)]
    r['n_distinct_letters']=len(c)
    r['quad_per_letter']=round(float(qscore(r['pt']))/tot,3)
    r['keylen']=a+b; r['ptlen']=tot
    r['sec']=round(time.time()-t0,1)
    out[f'{t}_{kind}_{a}_{b}']=r
    print(json.dumps({k:v for k,v in r.items() if k!='pt'},indent=None))
    print('  PT:',r['pt'])
json.dump(out,open('results/qk_repro.json','w'),indent=1)
