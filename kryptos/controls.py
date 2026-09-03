"""BOOT step 2: positive controls. All seven must round-trip."""
import numpy as np
from lib import *

ok = True
def check(name, got, want):
    global ok
    r = (got == want)
    ok &= r
    print(f"  {'PASS' if r else 'FAIL'}  {name}")
    if not r:
        print(f"        got  {got[:70]}")
        print(f"        want {want[:70]}")
    return r

print("=== LENGTH CHECK ===")
for k in CT:
    n = len(CT[k])
    p = len(PT[k]) if k in PT else None
    print(f"  {k:5s} ct={n:4d}  pt={p if p is not None else '-':>4}  n%9={n%9}  match={'ok' if p in (None,n) else 'MISMATCH'}")

print("\n=== ROUND-TRIP CONTROLS ===")
check("PK1  q3enc(PT1,[PROVENANCE])", q3enc(PT['pk1'], ['PROVENANCE']), CT['pk1'])
check("PK2  col_enc(PT2,[1,3,4,0,5,2,6])", col_enc(PT['pk2'], [1,3,4,0,5,2,6]), CT['pk2'])
k3 = q3enc('PENTIMENTO'*4, ['ORDINATE'])
check("PK3  q3enc(PT3,[q3enc(PENTIMENTOx4,ORDINATE)])", q3enc(PT['pk3'], [k3]), CT['pk3'])
check("PK4  q3enc(col_enc(PT4,(6,2,3,5,1,4,0,7)),[OCHRE,VERDIGRIS])",
      q3enc(col_enc(PT['pk4'], (6,2,3,5,1,4,0,7)), ['OCHRE','VERDIGRIS']), CT['pk4'])
t5 = col_enc(PT['pk5'], (5,4,2,6,7,0,1,3))
c5 = ''.join(KA[(KAI[ch]+KAI[PT['pk4'][i % len(PT['pk4'])]]) % 26] for i, ch in enumerate(t5))
check("PK5  vigenere(col_enc(PT5),running=PT4)", c5, CT['pk5'])
check("PK6  q3enc(col(col(PT6,H),H2),[PORTAL])",
      q3enc(col_enc(col_enc(PT['pk6'], [1,3,0,4,8,2,6,7,5]), [4,2,8,1,6,7,0,3,5]), ['PORTAL']), CT['pk6'])

# PK7: p = D*c - off[:, block%2] over KA indices
D = np.array([[10,16,3],[8,9,0],[9,11,15]])
OFF = np.array([[7,11],[19,7],[19,17]])
c = to_idx(CT['pk7']).astype(int)
p7 = []
for b in range(len(c)//3):
    v = c[3*b:3*b+3]
    p7.extend(((D @ v) - OFF[:, b % 2]) % 26)
check("PK7  Hill 3x3 + period-2 additive", to_str(np.array(p7)), PT['pk7'])

print("\n=== INVERSE FUNCTION CONTROLS ===")
check("col_dec inverts col_enc (PK2)", col_dec(CT['pk2'], [1,3,4,0,5,2,6]), PT['pk2'])
check("col_dec inverts col_enc (PK4)", col_dec(col_enc(PT['pk4'], (6,2,3,5,1,4,0,7)), (6,2,3,5,1,4,0,7)), PT['pk4'])
check("q3dec inverts q3enc", q3dec(CT['pk1'], ['PROVENANCE']), PT['pk1'])
check("q3dec 2-key inverts", q3dec(CT['pk4'], ['OCHRE','VERDIGRIS']), col_enc(PT['pk4'], (6,2,3,5,1,4,0,7)))

print("\n=== VERDICT ===")
print("  ALL CONTROLS PASS" if ok else "  *** HARNESS BROKEN ***")
raise SystemExit(0 if ok else 1)
