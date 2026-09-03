import sys, os, time; sys.path.insert(0,'.')
import numpy as np
from lib import KA, AZ, CT, PT, q3enc
import mk_lib as M

byl = M.load_words()
Wc = {}
def W(L, ka): 
    k=(L,ka)
    if k not in Wc: Wc[k]=M.wordmat(byl[L], ka)
    return Wc[k]

def rank_of(words, sc, target):
    i = words.index(target)
    return int((sc > sc[i]).sum())+1, float(sc[i])

# --- PC1: PK1, single word period 10, PROVENANCE, full-decrypt IoC ---
C = M.to_idx(CT['pk1'], KA); n=len(C)
t0=time.time()
cm = M.map_mod(n,10,10)
sc = M.score_parts(C, W(10,KA), [(np.arange(n), cm)], 'sub')
b,m,s,z = M.zstat(sc); r,v = rank_of(byl[10], sc, 'PROVENANCE')
print(f"PC1 PK1 single-word len10: rank(PROVENANCE)={r}/{len(sc)} ioc={v:.4f} best={b:.4f} z={z:.2f} {time.time()-t0:.1f}s")

# --- PC2: PK3, two-word general-L decoupled, L=40, a=10 b=8 ---
C3 = M.to_idx(CT['pk3'], KA); n3=len(C3)
t0=time.time()
L,a,b_=40,10,8
fa = M.map_mod(n3,L,a); gb = M.map_mod(n3,L,b_)
partsA = M.parts_by_group(gb, fa)
scA = M.score_parts(C3, W(a,KA), partsA, 'sub')
bb,mm,ss,zA = M.zstat(scA); rA,vA = rank_of(byl[a], scA, 'PENTIMENTO')
partsB = M.parts_by_group(fa, gb)
scB = M.score_parts(C3, W(b_,KA), partsB, 'sub')
b2,m2,s2,zB = M.zstat(scB); rB,vB = rank_of(byl[b_], scB, 'ORDINATE')
print(f"PC2 PK3 L=40 a=10: rank(PENTIMENTO)={rA}/{len(scA)} z={zA:.2f}  |  b=8 rank(ORDINATE)={rB}/{len(scB)} z={zB:.2f}  {time.time()-t0:.1f}s")

# --- PC3: synthetic M1 with L != lcm, at n=144/153/504 ---
rng = np.random.default_rng(7)
src = (PT['pk6']+PT['pk2']+PT['pk3']+PT['pk5'])
def synth(n, W1, W2, L, mode='sub'):
    pt = src[:n]
    key = q3enc(W1*((L+len(W1)-1)//len(W1)), [W2])[:L]
    return q3enc(pt, [key]), pt
for n in (144,153,504):
    W1,W2 = 'CRUCIBLE','ANNEAL'   # a=8 b=6 lcm=24
    for L in (16, 32, 40):
        ct,pt = synth(n,W1,W2,L)
        Cs = M.to_idx(ct,KA)
        fa=M.map_mod(n,L,8); gb=M.map_mod(n,L,6)
        pa=M.parts_by_group(gb,fa); pb=M.parts_by_group(fa,gb)
        s1=M.score_parts(Cs,W(8,KA),pa,'sub'); s2=M.score_parts(Cs,W(6,KA),pb,'sub')
        r1,_=rank_of(byl[8],s1,W1); r2,_=rank_of(byl[6],s2,W2)
        _,_,_,z1=M.zstat(s1); _,_,_,z2=M.zstat(s2)
        print(f"PC3 synth n={n} L={L} (lcm=24): rank(W1)={r1} z={z1:.2f} | rank(W2)={r2} z={z2:.2f}  infoA={M.informative(pa)}/{len(pa)} infoB={M.informative(pb)}/{len(pb)}")

# --- timing of one full cell ---
C8 = M.to_idx(CT['pk8'], KA); n8=len(C8)
t0=time.time()
for (L,a,b_) in [(20,5,7),(24,8,7),(36,9,7)]:
    fa=M.map_mod(n8,L,a); gb=M.map_mod(n8,L,b_)
    M.score_parts(C8,W(a,KA),M.parts_by_group(gb,fa),'sub')
    M.score_parts(C8,W(b_,KA),M.parts_by_group(fa,gb),'sub')
print(f"TIMING 3 pk8 cells (both directions): {time.time()-t0:.2f}s")
t0=time.time()
C10 = M.to_idx(CT['pk10'], KA); n10=len(C10)
for (L,a,b_) in [(20,5,7),(24,8,7),(36,9,7)]:
    fa=M.map_mod(n10,L,a); gb=M.map_mod(n10,L,b_)
    M.score_parts(C10,W(a,KA),M.parts_by_group(gb,fa),'sub')
    M.score_parts(C10,W(b_,KA),M.parts_by_group(fa,gb),'sub')
print(f"TIMING 3 pk10 cells (both directions): {time.time()-t0:.2f}s")
