"""Second 'above ceiling' candidate in the same family: MB1 two-word outer-repeat, pk8,
joint IoC 0.06656 (real max over 4 config-runs) vs the claim's own null max 0.06493
(8 runs) and its focused 6-shuffle null max 0.06545 (24 runs).
The claim published the decrypt, so both the rank test and the language test are free."""
import sys, json; sys.path.insert(0,'.')
import numpy as np
sys.argv=['x']
from lib import CT, PT
import adm_engine as E
ENG=np.array([8.167,1.492,2.782,4.253,12.702,2.228,2.015,6.094,6.966,0.153,0.772,4.025,
 2.406,6.749,7.507,1.929,0.095,5.987,6.327,9.056,2.758,0.978,2.360,0.150,1.974,0.074]); ENG/=ENG.sum()
def prof(s):
    v=E.to_idx(s,E.AZ).astype(np.int64); c=np.bincount(v,minlength=26).astype(float); return c,len(s)
def chi2(s):
    c,n=prof(s); e=np.maximum(ENG*n,0.5)
    return float(((np.sort(c)[::-1]-np.sort(e)[::-1])**2/np.sort(e)[::-1]).sum())
def ioc(s):
    c,n=prof(s); return float((c*(c-1)).sum()/(n*(n-1)))
d=json.load(open('results/manufactured_keys.json'))['parts']['MB1_two_word_outer_repeat']
out={}
for tag in ('autopsy_best_pk8','autopsy_best_pk9'):
    p=d[tag]['plaintext']; c,n=prof(p); top=c.max()
    out[tag]={'n':n,'claimed_ioc':d[tag]['ioc'],'recomputed_ioc':round(ioc(p),5),
      'reproduces':abs(ioc(p)-d[tag]['ioc'])<1e-4,
      'top_letter_pct':round(100*top/n,2),
      'frac_of_ioc_from_top_letter':round((top*(top-1))/(n*(n-1))/ioc(p),4),
      'frac_of_ioc_from_top_TWO_letters':round(
         float(sum(x*(x-1) for x in np.sort(c)[::-1][:2]))/(n*(n-1))/ioc(p),4),
      'sorted_profile_chi2_vs_english_25df':round(chi2(p),1),
      'quadgram_per_letter_claimed':d[tag]['quadgram_per_letter']}
ref={}
for k in ('pk1','pk3','pk4','pk6','pk7'):
    s=PT[k][:153]; ref[k]={'ioc':round(ioc(s),5),'chi2':round(chi2(s),1)}
out['real_sibling_plaintexts_n153']=ref
out['rank_test_on_the_claims_own_numbers']={
 'MB1_pk8_real_max_over_config_runs':4,'MB1_pk8_real_max':0.06656,
 'MB1_pk8_focused_shuffle_null_runs':24,'MB1_pk8_focused_null_max':0.06545,
 'P_real_block_holds_the_max_under_exchangeability':round(4/(4+24),4),
 'note':'0.143. And this is one of several such comparisons made across the family, so even '
        'this is optimistic before any family-wise correction.'}
out['verdict']=('The MB1 pk8 "hit" fails the same two ways. Statistically its max-of-4 beating '
 'a max-of-24 null has null probability 0.14 by a pure rank argument. Substantively its '
 'decrypt is a two-letter spike: A and B alone supply most of the IoC, sorted-profile chi2 vs '
 'English is far outside the reference band set by the real sibling plaintexts.')
json.dump(out, open('results/adm_mb1.json','w'), indent=1)
print(json.dumps(out, indent=1))
