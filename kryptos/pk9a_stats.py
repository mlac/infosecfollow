import sys, json, numpy as np
sys.path.insert(0,'.')
from lib import *

ENG = np.array([8.167,1.492,2.782,4.253,12.702,2.228,2.015,6.094,6.966,0.153,0.772,4.025,2.406,
                6.749,7.507,1.929,0.095,5.987,6.327,9.056,2.758,0.978,2.360,0.150,1.974,0.074])/100.0
ENG = ENG/ENG.sum()

def census(s, alpha):
    ai={c:i for i,c in enumerate(alpha)}
    a=np.array([ai[c] for c in s]); return np.bincount(a,minlength=26)

def chi2_unif(cnt):
    n=cnt.sum(); e=n/26.0; return float(((cnt-e)**2/e).sum())
def chi2_eng(cnt):
    n=cnt.sum(); e=n*ENG; return float(((cnt-e)**2/e).sum())
def chi2_eng_sorted(cnt):
    n=cnt.sum(); o=np.sort(cnt)[::-1]; e=n*np.sort(ENG)[::-1]; return float(((o-e)**2/e).sum())
def IOC(cnt):
    n=cnt.sum(); return float((cnt*(cnt-1)).sum()/(n*(n-1)))

print("target  n     IoC      chi2U   chi2U_pred  chi2E_AZ  chi2E_KA  chi2Esort  max min")
for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7','pk8','pk9','pk10']:
    s=CT[k]; n=len(s)
    cAZ=census(s,AZ); cKA=census(s,KA)
    i=IOC(cAZ); pred=26*(n-1)*i+26-n
    print(f"{k:5s} {n:4d}  {i:.4f}  {chi2_unif(cAZ):7.2f}  {pred:9.2f}  {chi2_eng(cAZ):8.1f}  {chi2_eng(cKA):8.1f}  {chi2_eng_sorted(cAZ):8.1f}  {cAZ.max():3d} {cAZ.min():3d}")
print()
print("solved-plaintext IoCs (setter's own English):")
for k in sorted(PT): print(f"  {k}: n={len(PT[k])} IoC={IOC(census(PT[k],AZ)):.4f}")

s=CT['pk9']; c=census(s,AZ)
print("\nPK9 census (AZ literal):")
for i in range(26): print(f"  {AZ[i]} {c[i]:3d}", end='' if (i+1)%6 else '\n')
print()
print("coincidence budget: total pairs", int((c*(c-1)).sum()), " expected uniform", 144*143/26)
ordr=np.argsort(c)[::-1]
tot=(c*(c-1)).sum()
for j in ordr[:6]:
    print(f"  {AZ[j]}: n={c[j]:2d} pairs={c[j]*(c[j]-1):4d} = {100*c[j]*(c[j]-1)/tot:.1f}% of coincidences")
# IoC dropping the top-2 letters
for drop in [[],[ordr[0]],[ordr[0],ordr[1]]]:
    cc=c.copy(); cc[drop]=0; n2=cc.sum()
    print("  drop",[AZ[d] for d in drop],"-> n=",n2," IoC=",round(float((cc*(cc-1)).sum()/(n2*(n2-1))),4))
