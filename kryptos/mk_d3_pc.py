"""Positive control for the depth-3 decoupled solver AND for concat/interleave, n=144/153/504."""
import sys, os, time, json; sys.path.insert(0,'.')
import numpy as np
from lib import KA, AZ, CT, PT, q3enc
import mk_lib as M
byl = M.load_words(3,12)
WK = {L: M.wordmat(byl[L], KA) for L in byl}
WKR = {L: WK[L][:, ::-1].copy() for L in byl}
src = (PT['pk6']+PT['pk2']+PT['pk3']+PT['pk5']+PT['pk7'])
ki = {c:i for i,c in enumerate(KA)}
OUT=[]
def rep(**kw): OUT.append(kw); print(' | '.join(f'{k}={v}' for k,v in kw.items()), flush=True)
def rank(words, sc, w):
    i=words.index(w); return int((sc>sc[i]).sum())+1

# ---- depth 3 ----
W1,W2,W3 = 'ARC','KILN','FORGE'      # a=3 b=4 c=5
for n in (144,153,504):
    for L in (12, 9):
        i=np.arange(n)
        w1=np.array([ki[c] for c in W1]); w2=np.array([ki[c] for c in W2]); w3=np.array([ki[c] for c in W3])
        S=(w1[(i%L)%3]+w2[(i%L)%4]+w3[(i%L)%5])%26
        ct=''.join(KA[(ki[c]+int(S[t]))%26] for t,c in enumerate(src[:n]))
        C=M.to_idx(ct,KA)
        fa=M.map_mod(n,L,3); fb=M.map_mod(n,L,4); fc=M.map_mod(n,L,5)
        rs=[]; zs=[]
        for (own,o1,o2,la,tw) in ((fa,fb,fc,3,W1),(fb,fa,fc,4,W2),(fc,fa,fb,5,W3)):
            parts=M.parts_by_group(o1*26+o2, own)
            s=M.score_parts(C,WK[la],parts,'sub')
            if s is None: rs.append(None); zs.append(None); continue
            rs.append(rank(byl[la],s,tw)); zs.append(round(M.zstat(s)[3],2))
        rep(ctl='SYN depth3 ARC/KILN/FORGE', n=n, L=L, ranks=rs, z=zs,
            RECOVERED=all(r==1 for r in rs if r is not None))

# ---- concat / interleave (identical pipeline to mk_cat.py) ----
def layoutC(n,a,b):
    i=np.arange(n); P=a+b; r=i%P
    pA=np.nonzero(r<a)[0]; pB=np.nonzero(r>=a)[0]
    fA=np.zeros(n,dtype=np.int64); fA[pA]=r[pA]
    fB=np.zeros(n,dtype=np.int64); fB[pB]=r[pB]-a
    return pA,r[pA],pB,r[pB]-a,fA,fB
def layoutD(n,a,b):
    i=np.arange(n); pA=np.nonzero(i%2==0)[0]; pB=np.nonzero(i%2==1)[0]
    fA=np.zeros(n,dtype=np.int64); fA[pA]=(pA//2)%a
    fB=np.zeros(n,dtype=np.int64); fB[pB]=(pB//2)%b
    return pA,(pA//2)%a,pB,(pB//2)%b,fA,fB
def joint_masked(C,WA,WB,fA,fB,mA,mB,iA,iB,mode='sub'):
    n=len(C)
    SA=np.zeros((len(iA),n),dtype=np.int16); SA[:,mA]=WA[iA][:,fA[mA]]
    SB=np.zeros((len(iB),n),dtype=np.int16); SB[:,mB]=WB[iB][:,fB[mB]]
    base=C.astype(np.int16); best=-1; bi=bj=0
    for x in range(SA.shape[0]):
        R=(base[None,:]-SA[x][None,:]-SB)%26
        v=M.ioc_rows_fast(R); j=int(v.argmax())
        if v[j]>best: best,bi,bj=float(v[j]),x,j
    return best,bi,bj
W1,W2='CRUCIBLE','ANNEAL'
for kind in ('C','CR','D'):
    for n in (144,153,504):
        a,b=len(W1),len(W2); i=np.arange(n)
        w1=np.array([ki[c] for c in W1]); w2=np.array([ki[c] for c in W2])
        if kind=='C':   S=np.concatenate([w1,w2])[i%(a+b)]
        elif kind=='CR':S=np.concatenate([w1,w2[::-1]])[i%(a+b)]
        else:
            S=np.zeros(n,dtype=int); S[0::2]=w1[(np.arange(len(S[0::2])))%a]; S[1::2]=w2[(np.arange(len(S[1::2])))%b]
        ct=''.join(KA[(ki[c]+int(S[t]))%26] for t,c in enumerate(src[:n]))
        C=M.to_idx(ct,KA)
        best=(-1,None)
        for aa in range(3,13):
            for bb in range(3,13):
                pA,cA,pB,cB,fA,fB = (layoutC(n,aa,bb) if kind in ('C','CR') else layoutD(n,aa,bb))
                WB = WKR[bb] if kind=='CR' else WK[bb]
                sA=M.score_parts(C,WK[aa],[(pA,cA)],'sub'); sB=M.score_parts(C,WB,[(pB,cB)],'sub')
                iA=np.argsort(-sA)[:200]; iB=np.argsort(-sB)[:200]
                j,x,y=joint_masked(C,WK[aa],WB,fA,fB,pA,pB,iA,iB)
                if j>best[0]: best=(j,(aa,bb,byl[aa][int(iA[x])],byl[bb][int(iB[y])]))
        ok = best[1][0]==a and best[1][1]==b and best[1][2]==W1 and best[1][3]==W2
        rep(ctl=f'SYN {kind} concat/interleave', n=n, best=str(best[1]), joint_ioc=round(best[0],4), RECOVERED=ok)
json.dump(OUT, open('results/mk_positive_controls_2.json','w'), indent=1)
print('PC2 DONE')
