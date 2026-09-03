import sys, time, json, numpy as np
sys.path.insert(0,'/home/user/infosecfollow/kryptos')
from mtv_kern import *
from lib import KA, AZ, CT
from gk_common import shuffled, idx, keystream, mixalpha, make_syn
from lib import col_enc

out = {}
t0 = time.time()
ai = {ch:i for i,ch in enumerate(KA)}
c  = np.array([ai[x] for x in CT['pk9']], np.int8)

# 1. FULL 10^7 enumeration of the claimed cell, my own code
r = enumerate_full(c, 7, 10, 0, -1, topk=8)
out['pk9.real.KA.m.aca'] = {'best':[round(float(x),6) for x in r['best']],
    'primers':[list(map(int,p)) for p in r['primer']],
    'mean':round(r['mean'],6), 'sd':round(r['sd'],6), 'count':int(r['count'])}
print('REAL top8', out['pk9.real.KA.m.aca']['best'])
print('REAL top primer', out['pk9.real.KA.m.aca']['primers'][0], 'mean %.6f sd %.6f'%(r['mean'],r['sd']))

# 2. cross-check three more claimed cells (AZ, +sign, and a shuffle-null cell from the claim)
for tag, s, alpha, sign in [('pk9.real.KA.p', CT['pk9'], KA, +1),
                            ('pk9.real.AZ.m', CT['pk9'], AZ, -1),
                            ('pk9.nul1.KA.m', shuffled(CT['pk9'],1001), KA, -1),
                            ('pk9.nul2.KA.p', shuffled(CT['pk9'],2002), KA, +1)]:
    cc = np.array(idx(s, alpha), np.int8)
    rr = enumerate_full(cc, 7, 10, 0, sign, topk=1)
    out[tag] = {'best':round(float(rr['best'][0]),6), 'primer':list(map(int,rr['primer'][0]))}
    print(tag, out[tag])

# 3. positive control in MY kernel: synthetic form A at n=144 with a known primer
mix = mixalpha(12345)
pt144 = CT['pk9']  # placeholder length only; use a real English plaintext
pt = (PTSRC := __import__('lib').PT)
src = ''.join(pt[k] for k in sorted(pt))
src = ''.join(ch for ch in src if ch.isalpha())[:144]
true_primer = [3,1,4,1,5,9,2]
syn = make_syn(src, true_primer, 0, 10, mix, alpha=AZ, form='A', enc_sign=+1)
cs = np.array(idx(syn, AZ), np.int8)
rp = enumerate_full(cs, 7, 10, 0, -1, topk=3)
rank1 = list(map(int, rp['primer'][0])) == true_primer
out['positive_control'] = {'n':144,'true_primer':true_primer,
    'top3':[round(float(x),6) for x in rp['best']],
    'top3_primers':[list(map(int,p)) for p in rp['primer']],
    'true_at_rank1':bool(rank1), 'mean':round(rp['mean'],6),'sd':round(rp['sd'],6)}
print('POSCTRL', out['positive_control'])

# 3b. same synthetic with a width-9 columnar UNDERNEATH
import random
perm = tuple(random.Random(7).sample(range(9),9))
syn2 = make_syn(src, true_primer, 0, 10, mix, alpha=AZ, form='A', enc_sign=+1, perm=perm)
cs2 = np.array(idx(syn2, AZ), np.int8)
rp2 = enumerate_full(cs2, 7, 10, 0, -1, topk=3)
out['positive_control_columnar'] = {'perm':list(perm),
    'top3':[round(float(x),6) for x in rp2['best']],
    'true_at_rank1':bool(list(map(int,rp2['primer'][0]))==true_primer)}
print('POSCTRL-COL', out['positive_control_columnar'])

out['wall_sec'] = round(time.time()-t0,1)
json.dump(out, open('results/mtv_repro.json','w'), indent=1)
print('WALL', out['wall_sec'])
