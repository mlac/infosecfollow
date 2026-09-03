"""Is the SURVIVING family (few alphabets, aperiodic order) attackable at n=144?
Direct test: search for the partition of the 144 positions into k equal classes that maximizes
mean per-class IoC.  If a random SHUFFLE of PK9 admits partitions just as good, the partition
carries no information and the family is undecidable at this length -- for ANY solver."""
import sys, json, time, numpy as np
sys.path.insert(0,'.')
from lib import *
rng=np.random.default_rng(31337); t0=time.time(); n=144
def best_partition(txt,k,restarts=20,iters=250,rg=None):
    sz=n//k; best=-1
    for _ in range(restarts):
        asg=np.repeat(np.arange(k),sz); rg.shuffle(asg)
        cnt=np.zeros((k,26),dtype=np.int64)
        for i in range(n): cnt[asg[i],txt[i]]+=1
        for _ in range(iters):
            # gain of swapping a letter x in class A with a letter y in class B
            G=2*(cnt[:,None,None,:]+cnt[None,:,:,None]-cnt[:,None,:,None]-cnt[None,:,None,:])+4
            avail=np.zeros((k,26),dtype=bool)
            for c in range(k): avail[c]=cnt[c]>0
            mask=avail[:,None,:,None]&avail[None,:,None,:]
            eye=np.eye(k,dtype=bool); mask&=~eye[:,:,None,None]
            G=np.where(mask,G,-10**9)
            f=int(np.argmax(G)); g=G.ravel()[f]
            if g<=0: break
            A,B,x,y=np.unravel_index(f,G.shape)
            cnt[A,x]-=1; cnt[A,y]+=1; cnt[B,y]-=1; cnt[B,x]+=1
        s=float((cnt*(cnt-1)).sum()/(k*sz*(sz-1)))
        best=max(best,s)
    return best
C9=np.array([AZ.index(c) for c in CT['pk9']])
NSH=30
res={}
print(f"{'k':>3} {'classlen':>8} {'PK9 best':>9} {'shuffle mean':>13} {'sd':>7} {'shuffle max':>11} {'z':>6} {'p_emp':>6}")
for k in [2,3,4,6]:
    rg=np.random.default_rng(1000+k)
    obs=best_partition(C9,k,rg=rg)
    nul=np.array([best_partition(rg.permutation(C9),k,rg=rg) for _ in range(NSH)])
    z=(obs-nul.mean())/nul.std(ddof=1)
    print(f"{k:3d} {n//k:8d} {obs:9.4f} {nul.mean():13.4f} {nul.std(ddof=1):7.4f} {nul.max():11.4f} {z:+6.2f} {float((nul>=obs).mean()):6.3f}")
    res[k]={'classlen':n//k,'obs':obs,'null_mean':float(nul.mean()),'null_sd':float(nul.std(ddof=1)),
            'null_max':float(nul.max()),'z':float(z),'p_emp':float((nul>=obs).mean()),'nshuffle':NSH}
# reference: what a REAL k-alphabet cipher scores at n=144
CORP=np.concatenate([np.array([AZ.index(c) for c in PT[q]],dtype=np.int64) for q in sorted(PT)])
print("\nreference -- best partition score for a TRUE k-alphabet aperiodic cipher at n=144:")
for k in [2,3,4]:
    rg=np.random.default_rng(500+k); vals=[]
    for _ in range(8):
        st=rg.integers(0,len(CORP)-n); P=CORP[st:st+n]
        sub=rg.permutation(26)[:k]; a=np.repeat(np.arange(k),n//k); rg.shuffle(a)
        Cx=(P+sub[a])%26
        vals.append(best_partition(Cx,k,rg=rg))
    print(f"  true k={k}: best-partition IoC {np.mean(vals):.4f} (vs PK9 {res[k]['obs']:.4f},"
          f" shuffle-null max {res[k]['null_max']:.4f})  -- true cipher NOT separated from noise"
          if np.mean(vals)<res[k]['null_max'] else f"  true k={k}: {np.mean(vals):.4f} SEPARATES")
    res[k]['true_cipher_score']=float(np.mean(vals))
json.dump(res,open('results/pk9_partition.json','w'),indent=1)
print(f"\nwall {time.time()-t0:.0f}s")
