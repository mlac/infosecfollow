"""Autopsy of the claimed hit: if primer 2546754 were right, the residual (c - k) mod 26 must be
MIX(P) -- a MONOALPHABETIC image of the (possibly transposed) plaintext.  Two consequences:
  (a) a monoalphabetic hill-climb on it must reach English quadgram scores (~ -4.3 .. -4.9 at n=144);
  (b) its SORTED unigram profile must look English (transposition-invariant, no climb needed).
Matched null = the residuals of the winning primers from the IDENTICAL 10^7 searches run on
letter-shuffled copies (artifact top-1 primers for nul1/nul2, all recurrences and signs, KA).
Positive control = the residual of the TRUE primer on a synthetic of the same length.
"""
import sys, json, random, numpy as np
sys.path.insert(0,'/home/user/infosecfollow/kryptos')
from lib import KA, AZ, CT, PT, ioc
from gk_common import shuffled, idx, keystream, mixalpha, make_syn
Q = np.load('quadgrams.npy')
ENG = np.array([8.167,1.492,2.782,4.253,12.702,2.228,2.015,6.094,6.966,0.153,0.772,4.025,2.406,
 6.749,7.507,1.929,0.095,5.987,6.327,9.056,2.758,0.978,2.360,0.150,1.974,0.074])/100.0

def qscore(a):
    a = np.asarray(a, np.int64)
    k = ((a[:-3]*26 + a[1:-2])*26 + a[2:-1])*26 + a[3:]
    return float(Q[k].mean())

def climb(a, restarts=14, iters=4000, seed=0):
    rng = random.Random(seed); best = -99; bk = None
    for r in range(restarts):
        key = list(range(26)); rng.shuffle(key)
        k = np.array(key); cur = qscore(k[a])
        for it in range(iters):
            i, j = rng.randrange(26), rng.randrange(26)
            if i == j: continue
            k[i], k[j] = k[j], k[i]
            s = qscore(k[a])
            if s > cur: cur = s
            else: k[i], k[j] = k[j], k[i]
        if cur > best: best, bk = cur, k.copy()
    return best, bk

def profile_chi2(a):
    h = np.bincount(np.asarray(a), minlength=26).astype(float); h /= h.sum()
    return float((((np.sort(h)[::-1] - np.sort(ENG)[::-1])**2)/np.sort(ENG)[::-1]).sum())

def residual(txt, alpha, primer, rec, sign, mod=10):
    c = np.array(idx(txt, alpha)); k = np.array(keystream(primer, len(c), rec, mod))
    return (c + sign*k) % 26

out = {}
# ---- the claimed hit
res = residual(CT['pk9'], KA, [2,5,4,6,7,5,4], 0, -1)
q, key = climb(res, seed=1)
out['claimed_hit'] = {'primer':[2,5,4,6,7,5,4],'ioc':round(ioc(''.join(AZ[v] for v in res)),6),
    'hillclimb_q':round(q,4),'profile_chi2':round(profile_chi2(res),4),
    'decrypt_head':''.join(AZ[key[v]] for v in res)[:96]}
print('CLAIM', out['claimed_hit']['hillclimb_q'], out['claimed_hit']['profile_chi2'])
print('   ', out['claimed_hit']['decrypt_head'])

# ---- matched null: winning primers of identical searches on shuffled copies
arts = json.load(open('results/gromark_L7_mod10.json'))
recmap = {'aca':0,'lag1':1,'fib':2,'subaca':3}
nq = []; nchi = []
for run in arts:
    rc = recmap[run['rec']]
    for name, t in run['targets'].items():
        p = name.split('.')
        if p[0]!='pk9' or p[1]=='real' or p[-1]=='CLS' or p[2]!='KA': continue
        sg = -1 if p[3]=='m' else +1
        txt = shuffled(CT['pk9'], 1001 if p[1]=='nul1' else 2002)
        r = residual(txt, KA, t['top'][0]['primer'], rc, sg)
        qq,_ = climb(r, seed=hash(name)%1000)
        nq.append(qq); nchi.append(profile_chi2(r))
        print('  null %-18s q=%.4f chi2=%.4f best=%.6f'%(name,qq,profile_chi2(r),t['top'][0]['score']), flush=True)
out['matched_null_winners'] = {'n':len(nq),
    'hillclimb_q':{'mean':round(float(np.mean(nq)),4),'sd':round(float(np.std(nq)),4),
                   'min':round(float(np.min(nq)),4),'max':round(float(np.max(nq)),4)},
    'profile_chi2':{'mean':round(float(np.mean(nchi)),4),'sd':round(float(np.std(nchi)),4),
                    'min':round(float(np.min(nchi)),4),'max':round(float(np.max(nchi)),4)}}
out['claimed_hit']['z_hillclimb_vs_null'] = round((q-np.mean(nq))/np.std(nq),2)
out['claimed_hit']['z_profile_vs_null']   = round((profile_chi2(res)-np.mean(nchi))/np.std(nchi),2)

# ---- positive control: TRUE primer residual on a synthetic of the same length
src = ''.join(PT[k] for k in sorted(PT)); src = ''.join(c for c in src if c.isalpha())[:144]
mix = mixalpha(12345); tp = [3,1,4,1,5,9,2]
syn = make_syn(src, tp, 0, 10, mix, alpha=AZ, form='A', enc_sign=+1)
rr = residual(syn, AZ, tp, 0, -1)
qp, kp = climb(rr, seed=5)
out['positive_control_true_primer'] = {'hillclimb_q':round(qp,4),
    'profile_chi2':round(profile_chi2(rr),4),
    'ioc':round(ioc(''.join(AZ[v] for v in rr)),6),
    'decrypt_head':''.join(AZ[kp[v]] for v in rr)[:96]}
print('POSCTRL', out['positive_control_true_primer'])
json.dump(out, open('results/mtv_autopsy.json','w'), indent=1)
print('WROTE results/mtv_autopsy.json')
