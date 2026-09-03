"""ADM = ADversarial verification of Manufactured-long-key family.
Independent reimplementation of the M-A single-word headline. Imports NOTHING from mk_lib.
"""
import sys, json; sys.path.insert(0,'.')
import numpy as np
from lib import CT
KA = "KRYPTOSABCDEFGHIJLMNQUVWXZ"
AZ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALPH = {'KA':KA,'AZ':AZ}

def idx(s, al):
    d = {c:i for i,c in enumerate(al)}
    return np.array([d[c] for c in s], dtype=np.int64)

def ioc(v):
    v = np.asarray(v)
    c = np.bincount(v, minlength=26).astype(float)
    L = len(v)
    return float((c*(c-1)).sum()/(L*(L-1)))

# quadgram model
Q = np.load('quadgrams.npy')   # flat 26^4, A-Z index order
def quad(v):  # v = indices 0..25 read as A-Z
    a = np.asarray(v, dtype=np.int64)
    k = a[:-3]*17576 + a[1:-2]*676 + a[2:-1]*26 + a[3:]
    return float(Q[k].mean())

def build_stream(word, a, name, n, ka):
    """Return keystream S (len n) as indices on key alphabet ka, or (colmaps, W) semantics."""
    kal = ALPH[ka]
    W = idx(word, kal)
    i = np.arange(n)
    if name.startswith('revtrunc'):
        L = int(name[8:]); mm = (i % L) % a
        return (W[mm] + W[a-1-mm]) % 26
    if name.startswith('selftrunc'):
        L = int(name[9:]); mm = (i % L) % a
        return (W[mm] + W[mm]) % 26
    if name.startswith('trunc'):
        L = int(name[5:]); mm = (i % L) % a
        return W[mm]
    if name == 'plain':  return W[i % a]
    if name == 'self2W': return (W[i%a]+W[i%a]) % 26
    if name == 'revsum': return (W[i%a]+W[a-1-(i%a)]) % 26
    raise ValueError(name)

def decrypt(tgt, ta, ka, md, word, a, name):
    ct = CT[tgt]; n = len(ct)
    C = idx(ct, ALPH[ta])
    S = build_stream(word, a, name, n, ka)
    if md=='sub': R = (C - S) % 26
    elif md=='add': R = (C + S) % 26
    else: R = (S - C) % 26
    return R

CASES = [
 ("HEADLINE  pk9 revtrunc14 METALHEAD",  'pk9','KA','AZ','sub','METALHEAD',9,'revtrunc14', 0.06313),
 ("runner-up pk9 trunc14 SCHOENHERR",    'pk9','AZ','AZ','sub','SCHOENHERR',10,'trunc14',   0.06167),
 ("plain     pk9 plain MMORPGS",         'pk9','AZ','KA','add','MMORPGS',7,'plain',         0.05876),
]
out={}
for label,tgt,ta,ka,md,w,a,name,claimed in CASES:
    R = decrypt(tgt,ta,ka,md,w,a,name)
    v = ioc(R)
    # render the decrypt on both alphabets to read it
    txt_az = ''.join(AZ[x] for x in R)
    txt_ka = ''.join(KA[x] for x in R)
    cnt = np.bincount(R, minlength=26)
    top = int(cnt.max()); topi = int(cnt.argmax())
    n=len(R)
    out[label]={'claimed_ioc':claimed,'recomputed_ioc':round(v,5),
      'exact_match': abs(v-claimed)<5e-6,
      'n':n,'distinct_letters':int((cnt>0).sum()),
      'top_letter_count':top,'top_letter_pct':round(100*top/n,2),
      'frac_of_ioc_from_top_letter': round((top*(top-1))/(n*(n-1))/v,4),
      'quadgram_per_letter_AZreading': round(quad(R),3),
      'decrypt_AZ':txt_az,'decrypt_KA':txt_ka}
    print(f"{label}: claimed {claimed} recomputed {v:.5f} match={abs(v-claimed)<5e-6}")
    print("   AZ:",txt_az)
    print(f"   top letter {AZ[topi]} x{top} = {100*top/n:.1f}%  quad/letter {quad(R):.3f}  distinct {int((cnt>0).sum())}")

# ROUND TRIP: is re-encryption informative?
tgt,ta,ka,md,w,a,name='pk9','KA','AZ','sub','METALHEAD',9,'revtrunc14'
R = decrypt(tgt,ta,ka,md,w,a,name)
S = build_stream(w,a,name,len(R),ka)
Cre = (R + S) % 26
recon = ''.join(KA[x] for x in Cre)
out['round_trip']={'reencrypt_equals_published_ct': recon==CT['pk9'],
  'note':'VACUOUS: decrypt is DEFINED as C-S, so C=(C-S)+S holds for every key whatsoever.'}
print("round-trip reproduces published pk9 CT:", recon==CT['pk9'], "(vacuous by construction)")

# key length vs plaintext length
out['key_economy']={'key_letters':len(w),'plaintext_letters':len(R),
  'compression_ratio':round(len(R)/len(w),2),
  'note':'9 letters explaining 144 is a real economy IF the decrypt were language; it is not.'}
json.dump(out, open('results/adm_repro.json','w'), indent=1)
print("\nwrote results/adm_repro.json")
