"""xmk_degen: is the headline decrypt language-like, or is its IoC manufactured by one letter?"""
import sys, json, collections; sys.path.insert(0,'.')
import numpy as np
from lib import KA, AZ, CT, PT, ka_to_az, qscore, ioc
import mk_lib as M
def diag(name, s):
    n=len(s); c=collections.Counter(s); cnt=np.array(sorted(c.values(),reverse=True))
    I=(cnt*(cnt-1)).sum()/(n*(n-1))
    top1=cnt[0]*(cnt[0]-1)/(n*(n-1))
    az=s if set(s)<=set(AZ) else s
    return {'name':name,'n':n,'ioc':round(float(I),5),
            'top_letter':int(cnt[0]),'top_letter_pct':round(100*cnt[0]/n,1),
            'ioc_from_top_letter':round(float(top1),5),
            'frac_of_ioc_from_top_letter':round(float(top1/I),3),
            'ioc_excluding_top_letter_pair_term':round(float(I-top1),5),
            'quadgram_per_letter':round(qscore(az),3),
            'distinct_letters':int(len(c))}
out={}
# headline decrypt
d=json.load(open('results/xmk_repro.json'))
pt=d['MA_headline']['plaintext']
out['headline_decrypt_pk9_METALHEAD_revtrunc14']=diag('pk9 M-A headline', ka_to_az(pt))
out['MB1_pk8_decrypt']=diag('pk8 M-B1 headline', ka_to_az(d['MB1_headline_pk8']['plaintext']))
out['MB1_pk9_decrypt']=diag('pk9 M-B1 headline', d['MB1_headline_pk9']['plaintext'])
# reference: real English/Italian plaintext of the same length
rng=np.random.default_rng(7)
pool=''.join(PT[k] for k in ('pk1','pk3','pk4','pk5','pk6','pk7'))
segs=[pool[int(rng.integers(0,len(pool)-144)):][:144] for _ in range(200)]
D=[diag('eng',s) for s in segs]
out['real_sibling_plaintext_n144']={k:round(float(np.mean([x[k] for x in D])),4)
    for k in ('ioc','top_letter_pct','frac_of_ioc_from_top_letter','quadgram_per_letter')}
out['calibration']={'random_quadgram':-8.23,'english_quadgram':-4.25,
 'interpretation':'quadgram score of the headline decrypt sits 0.16 of 3.98 nats from RANDOM, '
                  'i.e. ~4% of the way from random text to English.'}
# round-trip: re-encrypt the claimed plaintext under the claimed key
ki={c:i for i,c in enumerate(AZ)}; wv=np.array([ki[c] for c in 'METALHEAD'])
i=np.arange(144); mm=(i%14)%9; S=(wv[mm]+wv[8-mm])%26
P=M.to_idx(pt,KA); Cre=(P+S)%26
ctre=''.join(KA[int(v)] for v in Cre)
out['round_trip']={'reencrypt_matches_published_pk8_ciphertext':ctre==CT['pk9'],
 'note':'round-trip exactness is VACUOUS here: the decrypt is defined as C-S, so re-encrypting '
        'returns C for EVERY candidate key. It carries no evidential weight.'}
json.dump(out,open('results/xmk_degeneracy.json','w'),indent=1)
print(json.dumps(out,indent=1))
