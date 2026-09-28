"""Cribs at EVERY offset, not just the two ends.

Key simplification, verified over 240 (structure, length, offset) comparisons with zero mismatches:
the constraint matrix R depends ONLY on (crib length, structure), not on where the crib sits. A
shift permutes which unknown u_f[j] each row uses, but the pattern of which rows share an unknown
is shift-invariant for contiguous positions. So one checker per (length, structure) serves every
offset, and the whole offset scan becomes a single matrix product per (crib, structure).

§A8/§F8 tested the corpus at prefix and suffix positions only. The series repeats phrases across
entries -- THE WHITESMITH, THE NEEDLE, THE LOST ARCHIVE OF PELLEGRIN, the Italian quotation from
PK2 -- so a recurring phrase could sit anywhere in the plaintext. The consistency test does not
care where the crib sits, only that the positions are known, so scanning offsets is just more
tests. Kept to a curated phrase list because the test count scales with offsets x corpus.
"""
import numpy as np, itertools, json, time
from math import gcd
from lib import KA, AZ, CT, PT
from crib_sweep import make_checker

BASE = [
 'THEWHITESMITHSAYS','THEWHITESMITHTOLDME','THEWHITESMITHSWORKSHOP','THEWHITESMITHISDEAD',
 'THELOSTARCHIVEOFPELLEGRIN','THEROUTETOTHELOSTARCHIVE','THEARCHIVEOFPELLEGRIN',
 'ONCEUNRAVELEDITREVEALS','THETHREADINSCRIBEDWITHLETTERS','TWELVEPRIORARCHIVISTS',
 'THEACCESSIONLOGSAYS','ANEEDLEFINEENOUGHTOSPLITAHAIR','FINEENOUGHTOSPLITAHAIR',
 'THEINNERDOOR','ANDOPENEDTHEINNERDOOR','THERESIDUEOFHISPRACTICE','ONEOFMYOWNMAKING',
 'INTHEMANNEROFANARCHIVIST','THEWHITESMITHBROUGHTFOOD','HISALPINEWORKSHOP',
 'UNAGOTANTOSOTTILEDALEGGERE','UNAGOTANTOSOTTILE','DALEGGEREQUALUNQUENODO',
 'QUALUNQUENODO','PELLEGRINSOWNHAND','WRITTENINPELLEGRINSOWNHAND',
 'IFISTUDYUNDERHIMFORTENYEARS','HEWILLLETMETAKEONEOFMYOWNMAKING',
 'IHAVEMADEPEACEWITHIT','THISISNOTMYCALLING','IWILLGOHOMESOON','ANDWILLGOHOMESOON',
 'THEGUTTERALONGTHEWALL','EXQUISITENEEDLES','HEMAKESONEEVERYDAY','LOSTCOUNTLONGAGO',
 'PURIFYINGHISMETAL','DRAWINGITINTOAFINEWIRE','BEFOREDRAWINGITINTOAFINEWIRE',
 'THENEEDLEPRICKMYFINGER','SOFINETHATITDREWNOBLOOD','ICARRIEDITTOTHEWHITESMITH',
 'ASTONEBARNSTACKEDWITHWINTERFODDER','ONEOFHISNEEDLESISHIDDENINTHEBARN',
 'IHAVEBEGUNTOWORK','THEOLDTOOLSOFHISTRADE','MYEYESAREDRAWNTOTHEGUTTER',
]
CRIBS = sorted({c for c in BASE if 12 <= len(c) <= 40})
STR  = [(p,) for p in range(2,25)]
STR += [(a,b) for a in range(3,17) for b in range(a+1,17)]
STR += [t for t in itertools.combinations(range(3,15),3)]
MAXFP = 1e-7
CK = {}; hits=[]; ntest=0; efp=0.0; t0=time.time()
for tag in ('pk8','pk9','pk10'):
    n=len(CT[tag])
    for an,al in (('KA',KA),('AZ',AZ)):
        ai={c:i for i,c in enumerate(al)}
        Cv=np.array([ai[c] for c in CT[tag]])
        for cr in CRIBS:
            m=len(cr)
            if m>n: continue
            P=np.array([ai[ch] for ch in cr])
            offs=np.arange(0, n-m+1)
            W=Cv[offs[:,None]+np.arange(m)[None,:]]          # (n-m+1, m) sliding windows
            Ks={'sub':(W-P)%26, 'beau':(W+P)%26}             # 'add' == -sub, redundant (F7)
            for st in STR:
                kk=(m, st)
                if kk not in CK: CK[kk]=make_checker(np.arange(m), st)
                R2,R13,r2,r13=CK[kk]
                fp=(2.0**-r2)*(13.0**-r13)
                if fp>MAXFP: continue
                for mode,K in Ks.items():
                    ok=np.ones(len(offs),bool)
                    if r2:  ok &= ((K@R2.T)%2==0).all(1)
                    if r13: ok &= ((K@R13.T)%13==0).all(1)
                    ntest+=len(offs); efp+=fp*len(offs)
                    for i in np.nonzero(ok)[0]:
                        hits.append({'target':tag,'alpha':an,'mode':mode,'crib':cr,
                                     'offset':int(offs[i]),'structure':list(st),'fp':fp})
        print(f"  {tag} {an}: cum {ntest:,} tests, {len(hits)} hits ({time.time()-t0:.0f}s)",flush=True)
json.dump({'n_cribs':len(CRIBS),'n_tests':ntest,'expected_fp':efp,'hits':hits},
          open('results/crib_offsets.json','w'),indent=1)
print(f"\n=== CRIBS AT EVERY OFFSET: {len(CRIBS)} recurring phrases x every position x 3 targets "
      f"x 2 alphabets x 2 modes x {len(STR)} structures ===")
print(f"  effective tests: {ntest:,}   expected false positives: {efp:.2e}   observed passes: {len(hits)}")
for h in hits[:25]: print("   HIT",h)
