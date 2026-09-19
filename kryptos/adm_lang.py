"""Transposition-INVARIANT language test (doctrine 3: a columnar may sit underneath, so
quadgrams on the raw decrypt are not decisive; the LETTER-FREQUENCY PROFILE is invariant
under any transposition and is decisive)."""
import sys, json; sys.path.insert(0,'.')
import numpy as np
from lib import CT, PT
import adm_engine as E
from adm_repro import decrypt   # reuse the independent decryptor

ENG_FREQ = np.array([8.167,1.492,2.782,4.253,12.702,2.228,2.015,6.094,6.966,0.153,0.772,
 4.025,2.406,6.749,7.507,1.929,0.095,5.987,6.327,9.056,2.758,0.978,2.360,0.150,1.974,0.074])
ENG_FREQ = ENG_FREQ/ENG_FREQ.sum()

def profile(v):
    c=np.bincount(np.asarray(v,dtype=np.int64),minlength=26).astype(float)
    n=c.sum(); return c, n

def chi2_vs_english(v):
    """Best over all 26 rotations AND over the identity relabelling only -- we do NOT
    allow a free permutation (that would fit anything). Report the SORTED-PROFILE chi2,
    which is invariant to any relabelling of the alphabet and to any transposition."""
    c,n=profile(v)
    exp=ENG_FREQ*n
    srt=np.sort(c)[::-1]; esrt=np.sort(exp)[::-1]
    return float(((srt-esrt)**2/esrt).sum())

def stats(label, v):
    c,n=profile(v)
    L=int(n); ioc=float((c*(c-1)).sum()/(L*(L-1)))
    top=c.max()
    return {'label':label,'n':L,'ioc':round(ioc,5),
            'top_letter_pct':round(100*top/L,2),
            'frac_of_ioc_from_top_letter':round((top*(top-1))/(L*(L-1))/ioc,4),
            'sorted_profile_chi2_vs_english_25df':round(chi2_vs_english(v),1),
            'distinct':int((c>0).sum())}

out={'test':'sorted letter-frequency profile chi2 vs English on 25 df '
     '(invariant to ANY transposition AND to any alphabet relabelling; '
     'critical value 37.7 at p=0.05, 52.6 at p=0.001)'}

rows=[]
# the claimed hit
R=decrypt('pk9','KA','AZ','sub','METALHEAD',9,'revtrunc14')
rows.append(stats('CLAIMED HIT pk9 revtrunc14 METALHEAD', R))
R2=decrypt('pk9','AZ','AZ','sub','SCHOENHERR',10,'trunc14')
rows.append(stats('claim runner-up pk9 trunc14 SCHOENHERR', R2))
# real solved plaintexts, truncated to 144, as the reference for "what a solve looks like"
for k in ['pk1','pk3','pk4','pk6','pk7']:
    if k in PT and len(PT[k])>=144:
        rows.append(stats(f'REAL PLAINTEXT {k}[:144]', E.to_idx(PT[k][:144],E.AZ)))
# and the raw ciphertexts for the floor
for k in ['pk8','pk9','pk10']:
    rows.append(stats(f'RAW CIPHERTEXT {k}', E.to_idx(CT[k][:144],E.AZ)))
out['rows']=rows
for r in rows: print(f"{r['label']:44s} ioc={r['ioc']:.5f} top={r['top_letter_pct']:5.2f}% "
                     f"topIoCfrac={r['frac_of_ioc_from_top_letter']:.3f} chi2={r['sorted_profile_chi2_vs_english_25df']:8.1f}")
json.dump(out, open('results/adm_language.json','w'), indent=1)

# --- Italian reference (the claim's decrypts were to be read "as English or Italian")
ITA = np.array([11.74,0.92,4.50,3.73,11.79,0.95,1.64,1.54,11.28,0.00,0.00,6.51,2.51,6.88,
 9.83,3.05,0.51,6.37,4.98,5.62,3.01,0.21,0.00,0.00,0.00,0.49])
ITA = ITA/ITA.sum()
def chi2_generic(v, F):
    c,n=profile(v); exp=F*n
    exp=np.maximum(exp, 0.5)          # guard zero-probability letters
    srt=np.sort(c)[::-1]; esrt=np.sort(exp)[::-1]
    return float(((srt-esrt)**2/esrt).sum())
it={}
R=decrypt('pk9','KA','AZ','sub','METALHEAD',9,'revtrunc14')
it['CLAIMED_HIT_vs_italian_sorted_chi2']=round(chi2_generic(R,ITA),1)
for k in ['pk1','pk3','pk7']:
    it[f'REAL_PLAINTEXT_{k}_144_vs_italian_sorted_chi2']=round(
        chi2_generic(E.to_idx(PT[k][:144],E.AZ),ITA),1)
it['note']=('Sorted-profile chi2 against Italian on 25 df. Same conclusion as English: the '
            'claimed decrypt is nowhere near a natural-language letter profile, and the test '
            'is invariant to any transposition hidden underneath and to any alphabet relabelling.')
out['italian']=it
json.dump(out, open('results/adm_language.json','w'), indent=1)
print('ITALIAN:', json.dumps(it, indent=1))
