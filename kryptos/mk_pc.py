"""Positive controls for every manufacture type in this family, at n=144/153/504,
plus the two REAL solved instances (PK1 period-10 PROVENANCE, PK3 q3enc(PENTIMENTOx4,ORDINATE)).
Each control runs the IDENTICAL search the blind sweep runs and reports the rank of the truth.
"""
import sys, os, time, json; sys.path.insert(0,'.')
import numpy as np
from math import lcm
from lib import KA, AZ, CT, PT, q3enc
import mk_lib as M

byl = M.load_words(3, 16)
WK = {L: M.wordmat(byl[L], KA) for L in byl}
WKR = {L: WK[L][:, ::-1].copy() for L in byl}
WCAT = {L: np.hstack([WK[L], WKR[L]]) for L in byl}
src = (PT['pk6'] + PT['pk2'] + PT['pk3'] + PT['pk5'] + PT['pk7'])
OUT = []
def rep(**kw):
    OUT.append(kw); print(' | '.join(f'{k}={v}' for k,v in kw.items()), flush=True)

def rank(words, sc, w):
    i = words.index(w); return int((sc > sc[i]).sum())+1, float(sc[i])

# ---------- 1. REAL solved instances ----------
C = M.to_idx(CT['pk1'], KA); n = len(C)
sc = M.score_parts(C, WK[10], [(np.arange(n), np.arange(n)%10)], 'sub')
r, v = rank(byl[10], sc, 'PROVENANCE'); b,mu,sd,z = M.zstat(sc)
rep(ctl='REAL PK1 single-word period10', n=n, rank=r, of=len(sc), ioc=round(v,4), z=round(z,2))

C = M.to_idx(CT['pk3'], KA); n = len(C); L,a,b_ = 40,10,8
fa = M.map_mod(n,L,a); gb = M.map_mod(n,L,b_)
sA = M.score_parts(C, WK[a], M.parts_by_group(gb,fa), 'sub')
sB = M.score_parts(C, WK[b_], M.parts_by_group(fa,gb), 'sub')
rA,_ = rank(byl[a], sA, 'PENTIMENTO'); rB,_ = rank(byl[b_], sB, 'ORDINATE')
iA = np.argsort(-sA)[:150]; iB = np.argsort(-sB)[:150]
j,x,y = M.joint_confirm(C, WK[a], WK[b_], fa, gb, iA, iB, 'sub')
rep(ctl='REAL PK3 two-word decoupled L=40', n=n, rankW1=rA, rankW2=rB,
    joint_ioc=round(j,4), joint_pair=f'{byl[a][int(iA[x])]}+{byl[b_][int(iB[y])]}')

# ---------- 2. single-word manufactures: full mk_single sweep on a synthetic ----------
sys.argv = ['x','pc','0']
import importlib.util
spec = importlib.util.spec_from_file_location('ms', 'mk_single.py')
def build_single(kind, W, n):
    a = len(W); i = np.arange(n); ki = {c:k for k,c in enumerate(KA)}
    w = np.array([ki[c] for c in W]); wr = w[::-1]
    if kind=='self2W':  S = (w[i%a]+w[i%a])
    elif kind=='revsum':S = (w[i%a]+wr[i%a])
    elif kind=='catrev':S = np.concatenate([w,wr])[i%(2*a)]
    elif kind=='prog':  S = (w[i%a]+w[(i//a)%a])
    elif kind=='KArun': S = (w[i%a]+np.array([ki[KA[t%26]] for t in range(n)]))
    elif kind.startswith('trunc'): Lx=int(kind[5:]); S = w[(i%Lx)%a]
    S = S % 26
    ct = ''.join(KA[(ki[c]+int(S[t]))%26] for t,c in enumerate(src[:n]))
    return ct
CONS = ['self2W','revsum','catrev','prog','KArun','trunc13']
TW = 'ALCHEMIST'   # a=9 ; trunc13 -> period 13, not a multiple of 9
for n in (144,153,504):
    for kind in CONS:
        ct = build_single(kind, TW, n); Cs = M.to_idx(ct, KA); allp = np.arange(n)
        # identical blind sweep: every construction x every word length
        best = (-1,None); truth = None
        i = np.arange(n)
        for aa in range(3,17):
            m = i % aa
            cands = [('plain', WK[aa], m), ('self2W', WK[aa], np.stack([m,m])),
                     ('revsum', WK[aa], np.stack([m, aa-1-m])), ('catrev', WCAT[aa], i%(2*aa)),
                     ('prog', WK[aa], np.stack([m,(i//aa)%aa])),
                     ('progrev', WK[aa], np.stack([m, aa-1-((i//aa)%aa)])),
                     ('KArun', WK[aa], m)]
            offs = {'KArun': np.array([{c:k for k,c in enumerate(KA)}[KA[t%26]] for t in range(n)],dtype=np.int16)}
            Ls = sorted({x for x in set(range(aa+1,2*aa))|{24,26,30,32,36,40,45,48} if x>aa and x%aa and x<=48})
            for Lx in Ls:
                cands.append((f'trunc{Lx}', WK[aa], (i%Lx)%aa))
            for (nm, Wv, cm) in cands:
                s = M.score_parts(Cs, Wv, [(allp,cm)], 'sub', offs.get(nm))
                k = int(s.argmax())
                if s[k] > best[0]: best = (float(s[k]), (nm, aa, byl[aa][k]))
                if nm == kind and aa == len(TW):
                    rr,_ = rank(byl[aa], s, TW); truth = rr
        hit = best[1][0]==kind and best[1][2]==TW
        rep(ctl=f'SYN single {kind}', n=n, truth_rank_in_own_cell=truth,
            global_argmax=f'{best[1][0]}/{best[1][2]}', ioc=round(best[0],4), RECOVERED=hit)

# ---------- 3. two-word M-B grid-level control (L != lcm) ----------
def build_two(W1, W2, L, n):
    key = q3enc(W1*((L+len(W1)-1)//len(W1)), [W2])[:L]
    return q3enc(src[:n], [key])
CELLS = []
for a in range(3,12):
    for b in range(3,12):
        if a==b: continue
        for k in range(1,6):
            Lx=k*a
            if Lx>55 or Lx%lcm(a,b)==0: continue
            CELLS.append((a,b,Lx))
for n in (144,504):
    W1,W2,Lx = 'CRUCIBLE','ANNEAL',32          # a=8 b=6 lcm=24, L=32 -> NOT the plain product
    ct = build_two(W1,W2,Lx,n); Cs = M.to_idx(ct,KA)
    best=(-1,None); t0=time.time()
    for (a,b,LL) in CELLS:
        fa=M.map_mod(n,LL,a); gb=M.map_mod(n,LL,b)
        pA=M.parts_by_group(gb,fa); pB=M.parts_by_group(fa,gb)
        if M.informative(pA)<2 or M.informative(pB)<2: continue
        sA=M.score_parts(Cs,WK[a],pA,'sub'); sB=M.score_parts(Cs,WK[b],pB,'sub')
        iA=np.argsort(-sA)[:150]; iB=np.argsort(-sB)[:150]
        j,x,y=M.joint_confirm(Cs,WK[a],WK[b],fa,gb,iA,iB,'sub')
        if j>best[0]: best=(j,(a,b,LL,byl[a][int(iA[x])],byl[b][int(iB[y])]))
    ok = best[1][:3]==(8,6,32) and best[1][3]==W1 and best[1][4]==W2
    rep(ctl='SYN two-word grid L!=lcm', n=n, cells=len(CELLS), best=str(best[1]),
        joint_ioc=round(best[0],4), RECOVERED=ok, sec=round(time.time()-t0,1))

json.dump(OUT, open('results/mk_positive_controls.json','w'), indent=1)
print('PC DONE')
