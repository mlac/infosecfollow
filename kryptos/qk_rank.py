"""Where does the TRUTH sit inside the two-stage search?  For genuine in-family interleave
instances, report the rank of each true word in the decoupled top-K preselect (K=200) and
the joint IoC of the true pair, versus the search's actual argmax."""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from lib import KA,AZ,PT,ioc
import mk_lib as M, qk_core as Q
byl=M.load_words(Q.AMIN,Q.AMAX)
def build(P,W1,W2,kind='D',ta='KA',ka='KA',md='add'):
    n=len(P); i=np.arange(n); a,b=len(W1),len(W2)
    posA,cmA,posB,cmB,fA,fB,mA,mB=Q.layout(kind,n,a,b)
    ki={c:j for j,c in enumerate(Q.ALPH[ka])}
    S=np.zeros(n,dtype=np.int64)
    S[posA]=[ki[W1[c]] for c in cmA]; S[posB]=[ki[W2[c]] for c in cmB]
    Pi=M.to_idx(P,Q.ALPH[ta])
    C=(Pi-S)%26 if md=='add' else (Pi+S)%26
    return ''.join(Q.ALPH[ta][x] for x in C)
def probe(P,W1,W2,kind='D',ta='KA',ka='KA',md='add'):
    a,b=len(W1),len(W2)
    ct=build(P,W1,W2,kind,ta,ka,md)
    C=M.to_idx(ct,Q.ALPH[ta]); n=len(C)
    posA,cmA,posB,cmB,fA,fB,mA,mB=Q.layout(kind,n,a,b)
    WA=M.wordmat(byl[a],Q.ALPH[ka]); WB=M.wordmat(byl[b],Q.ALPH[ka])
    sA=M.score_parts(C,WA,[(posA,cmA)],md); sB=M.score_parts(C,WB,[(posB,cmB)],md)
    iA=byl[a].index(W1); iB=byl[b].index(W2)
    rA=int((sA>sA[iA]).sum())+1; rB=int((sB>sB[iB]).sum())+1
    topA=np.argsort(-sA)[:Q.K]; topB=np.argsort(-sB)[:Q.K]
    j_true,_,_=Q.joint_masked(C,WA,WB,fA,fB,mA,mB,np.array([iA]),np.array([iB]),md)
    j_srch,x,y=Q.joint_masked(C,WA,WB,fA,fB,mA,mB,topA,topB,md)
    return {'W1':W1,'W2':W2,'a':a,'b':b,'kind':kind,'cfg':f'{ta}/{ka}/{md}','pt_ioc':round(ioc(P),5),
            'rank_W1':rA,'of':len(byl[a]),'rank_W2':rB,'of2':len(byl[b]),
            'W1_in_topK':bool(rA<=Q.K),'W2_in_topK':bool(rB<=Q.K),
            'joint_TRUE_pair':round(j_true,5),'joint_cell_argmax':round(j_srch,5),
            'cell_argmax_words':[byl[a][int(topA[x])],byl[b][int(topB[y])]]}
res=[]
for (t,s) in [('pk4',12),('pk1',12),('pk5',36)]:
    P=PT[t][s:s+144]
    res.append(dict(src=f'{t}[{s}]',**probe(P,'ALCHEMISTS','FURNACE')))
    res.append(dict(src=f'{t}[{s}]',**probe(P,'CRUCIBLE','ANNEAL')))
    res.append(dict(src=f'{t}[{s}]',**probe(P,'CRUCIBLE','ANNEAL',kind='C')))
for r in res: print(json.dumps(r))
json.dump(res,open('results/qk_truthrank.json','w'),indent=1)
