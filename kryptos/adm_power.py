"""What score would a TRUE in-family key have produced? Under H1 the search recovers the key
and the reported statistic is then, by definition, the IoC of the real plaintext itself."""
import sys, json; sys.path.insert(0,'.')
import numpy as np
from lib import PT
import adm_engine as E
def ioc(s):
    c=np.bincount(E.to_idx(s,E.AZ).astype(np.int64),minlength=26).astype(float)
    n=len(s); return round(float((c*(c-1)).sum()/(n*(n-1))),5)
out={'logic':('If pk9 really had a single-word manufactured key, the blind search would peel it '
  'and the decrypt would BE the plaintext, so the reported IoC would equal the plaintext IoC. '
  'The positive control confirms the search has that power at n=144: PK1 truncated to 144 '
  'returns PROVENANCE at rank 1 of the whole grid.')}
w={}
for k,v in PT.items():
    w[k]={'full_n':len(v),'ioc_full':ioc(v),'ioc_first144':ioc(v[:144]),
          'ioc_first153':ioc(v[:153]) if len(v)>=153 else None}
out['solved_sibling_plaintext_iocs']=w
a=[w[k]['ioc_first144'] for k in w]
out['sibling_plaintext_ioc_at_n144']={'min':min(a),'max':max(a),'mean':round(float(np.mean(a)),5)}
out['observed_pk9_claim']=0.06313
out['positive_control_pk1_trunc144_grid_max']=0.07012
out['finding']=(f'Every one of the seven solved Kryptos-family plaintexts has IoC '
 f'{min(a)}-{max(a)} in its first 144 letters. The claimed pk9 result, 0.06313, is BELOW ALL '
 f'SEVEN. So the claim is not merely statistically weak -- it is quantitatively too small to '
 f'be a solve of this puzzle family even if it had been statistically clean. The genuine '
 f'in-family positive control at the same length returned 0.07012.')
json.dump(out, open('results/adm_power.json','w'), indent=1)
print(json.dumps(out, indent=1))
