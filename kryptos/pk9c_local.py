"""PK9 localization: does the IoC excess concentrate in a block or a residue class?
Matched null = random PERMUTATIONS of PK9 itself (preserves the census exactly, so the
global IoC excess is held fixed and only POSITIONAL structure is tested)."""
import sys, json, time, numpy as np
sys.path.insert(0,'.')
from lib import *
rng=np.random.default_rng(20260903)
t0=time.time()

def idx(s): return np.array([AZ.index(c) for c in s],dtype=np.int64)

def ioc_of(a):
    n=len(a)
    if n<2: return 0.0
    c=np.bincount(a,minlength=26); return float((c*(c-1)).sum()/(n*(n-1)))

def classioc_vec(A,p):
    """A: (N,n) int array. returns (N,) mean IoC over residue classes mod p."""
    N,n=A.shape; out=np.zeros(N)
    for r in range(p):
        sub=A[:,r::p]; L=sub.shape[1]
        if L<2: continue
        cnt=np.zeros((N,26),dtype=np.int32)
        for x in range(26): cnt[:,x]=(sub==x).sum(1)
        out+=(cnt*(cnt-1)).sum(1)/(L*(L-1))
    return out/p

def blockioc_vec(A,k):
    """mean IoC over k contiguous equal blocks"""
    N,n=A.shape; out=np.zeros(N); b=n//k
    for j in range(k):
        sub=A[:,j*b:(j+1)*b]; L=sub.shape[1]
        cnt=np.zeros((N,26),dtype=np.int32)
        for x in range(26): cnt[:,x]=(sub==x).sum(1)
        out+=(cnt*(cnt-1)).sum(1)/(L*(L-1))
    return out/k

C9=idx(CT['pk9']); n=144
NSH=20000
SH=np.array([rng.permutation(C9) for _ in range(NSH)])
print(f"shuffle null built {NSH} x {n}  ({time.time()-t0:.0f}s)")
res={'n':n,'ioc':ioc_of(C9),'nshuffle':NSH,'residue':{},'block':{}}

print("\n=== RESIDUE-CLASS TEST (mean per-class IoC) ===")
print(" p   classlen   observed    null_mean   null_sd     z     p_emp   null_max")
for p in range(2,13):
    obs=classioc_vec(C9[None,:],p)[0]
    nul=classioc_vec(SH,p)
    m,s=nul.mean(),nul.std(ddof=1)
    z=(obs-m)/s; pe=float((nul>=obs).mean())
    print(f"{p:2d}   {n//p:4d}    {obs:.5f}   {m:.5f}   {s:.5f}  {z:+6.2f}  {pe:.4f}  {nul.max():.5f}")
    res['residue'][p]={'classlen':n//p,'obs':float(obs),'null_mean':float(m),'null_sd':float(s),
                       'z':float(z),'p_emp':pe,'null_max':float(nul.max())}

print("\n=== CONTIGUOUS-BLOCK TEST (mean per-block IoC) ===")
print(" k   blocklen   observed    null_mean   null_sd     z     p_emp")
for k in [2,3,4,6,8,9,12,16]:
    obs=blockioc_vec(C9[None,:],k)[0]
    nul=blockioc_vec(SH,k)
    m,s=nul.mean(),nul.std(ddof=1); z=(obs-m)/s; pe=float((nul>=obs).mean())
    print(f"{k:2d}   {n//k:4d}    {obs:.5f}   {m:.5f}   {s:.5f}  {z:+6.2f}  {pe:.4f}")
    res['block'][k]={'blocklen':n//k,'obs':float(obs),'null_mean':float(m),'null_sd':float(s),'z':float(z),'p_emp':pe}

print("\n=== PER-HALF / PER-THIRD raw IoC (where does the excess sit?) ===")
for k in [2,3,4]:
    b=n//k
    vals=[ioc_of(C9[j*b:(j+1)*b]) for j in range(k)]
    print(f"  {k} blocks of {b}: "+"  ".join(f"{v:.4f}" for v in vals))
    res['block'][k]['per_block']=vals

print("\n=== SLIDING WINDOW w=48, step 8 (raw IoC) ===")
w=48; sl=[(st,ioc_of(C9[st:st+w])) for st in range(0,n-w+1,8)]
print("  "+"  ".join(f"{st}:{v:.4f}" for st,v in sl))
res['sliding_w48']=[[int(a),float(b)] for a,b in sl]
# null for max window
nulmax=np.array([max(ioc_of(SH[i][st:st+w]) for st in range(0,n-w+1,8)) for i in range(2000)])
obsmax=max(v for _,v in sl)
print(f"  max window IoC obs={obsmax:.4f}  null mean={nulmax.mean():.4f} sd={nulmax.std(ddof=1):.4f} z={(obsmax-nulmax.mean())/nulmax.std(ddof=1):+.2f} p={float((nulmax>=obsmax).mean()):.4f}")
res['sliding_max']={'obs':float(obsmax),'null_mean':float(nulmax.mean()),'null_sd':float(nulmax.std(ddof=1)),
                    'z':float((obsmax-nulmax.mean())/nulmax.std(ddof=1)),'p_emp':float((nulmax>=obsmax).mean())}

print("\n=== DIGRAPH IoC (positional, adjacent pairs) ===")
def digioc(a):
    d=a[:-1]*26+a[1:]; c=np.bincount(d,minlength=676); m=len(d)
    return float((c*(c-1)).sum()/(m*(m-1)))
obs=digioc(C9); nul=np.array([digioc(SH[i]) for i in range(NSH)])
print(f"  obs={obs:.6f} null={nul.mean():.6f} sd={nul.std(ddof=1):.6f} z={(obs-nul.mean())/nul.std(ddof=1):+.2f} p={float((nul>=obs).mean()):.4f}")
res['digraph']={'obs':obs,'null_mean':float(nul.mean()),'null_sd':float(nul.std(ddof=1)),
                'z':float((obs-nul.mean())/nul.std(ddof=1)),'p_emp':float((nul>=obs).mean())}

print("\n=== FAMILYWISE: max |z| over the 11 residue periods, vs null of the same max ===")
nulz=np.zeros((NSH,11))
for j,p in enumerate(range(2,13)):
    v=classioc_vec(SH,p); nulz[:,j]=(v-v.mean())/v.std(ddof=1)
obsz=np.array([res['residue'][p]['z'] for p in range(2,13)])
mx=nulz.max(1)
print(f"  observed max z={obsz.max():+.2f}  null max-z mean={mx.mean():.2f} sd={mx.std(ddof=1):.2f} 95th={np.percentile(mx,95):.2f} p_emp={float((mx>=obsz.max()).mean()):.4f}")
res['familywise_residue']={'obs_max_z':float(obsz.max()),'null_maxz_mean':float(mx.mean()),
    'null_maxz_95':float(np.percentile(mx,95)),'null_maxz_max':float(mx.max()),'p_emp':float((mx>=obsz.max()).mean())}
json.dump(res,open('results/pk9_localization.json','w'),indent=1)
print(f"\nwall {time.time()-t0:.0f}s -> results/pk9_localization.json")
