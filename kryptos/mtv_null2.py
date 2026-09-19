"""Winning primers of the IDENTICAL 10^7 aca/KA/sign-1 search on 40 fresh shuffles of pk9,
so the residual autopsy statistics get a 40-draw matched null of their own."""
import sys, json, time, random, numpy as np
sys.path.insert(0,'/home/user/infosecfollow/kryptos')
from gk_common import *
from lib import CT
SEEDS=list(range(900001,900041))
t0=time.time()
tg=''.join(target('s%d'%s,0,-1,idx(shuffled(CT['pk9'],s),KA)) for s in SEEDS)
r=run(header(10,7,144,0,topk=1,enum=1)+tg,'/tmp/claude-0/-home-user-infosecfollow/88072dfe-db0a-5acd-9caa-27f75aea8fde/scratchpad/mtv2.spec')
assert r['executed']==10**7
Q=np.load('quadgrams.npy')
ENG=np.array([8.167,1.492,2.782,4.253,12.702,2.228,2.015,6.094,6.966,0.153,0.772,4.025,2.406,
 6.749,7.507,1.929,0.095,5.987,6.327,9.056,2.758,0.978,2.360,0.150,1.974,0.074])/100.
def qs(a):
    a=np.asarray(a,np.int64); k=((a[:-3]*26+a[1:-2])*26+a[2:-1])*26+a[3:]; return float(Q[k].mean())
def climb(a,restarts=14,iters=4000,seed=0):
    rng=random.Random(seed); best=-99
    for _ in range(restarts):
        key=list(range(26)); rng.shuffle(key); k=np.array(key); cur=qs(k[a])
        for _ in range(iters):
            i,j=rng.randrange(26),rng.randrange(26)
            if i==j: continue
            k[i],k[j]=k[j],k[i]; s=qs(k[a])
            if s>cur: cur=s
            else: k[i],k[j]=k[j],k[i]
        best=max(best,cur)
    return best
def chi2(a):
    h=np.bincount(np.asarray(a),minlength=26).astype(float); h/=h.sum()
    return float((((np.sort(h)[::-1]-np.sort(ENG)[::-1])**2)/np.sort(ENG)[::-1]).sum())
rows=[]
for s in SEEDS:
    t=r['targets']['s%d'%s]; pr=t['top'][0]['primer']
    c=np.array(idx(shuffled(CT['pk9'],s),KA)); k=np.array(keystream(pr,144,0,10))
    res=(c-k)%26
    rows.append({'seed':s,'best':round(t['top'][0]['score'],6),'primer':pr,
                 'chi2':round(chi2(res),4),'q':round(climb(res,seed=s),4)})
    print(rows[-1],flush=True)
json.dump({'wall_sec':round(time.time()-t0,1),'rows':rows},open('results/mtv_null2.json','w'),indent=1)
print('WROTE results/mtv_null2.json %.0fs'%(time.time()-t0))
