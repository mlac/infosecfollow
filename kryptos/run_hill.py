import json, sys
from hill_blind import run
from lib import KA, AZ
tag = sys.argv[1]
res = run(tag, ks=[2,3,4], Ps=[1,2,3,4,6], alphas=[('KA',KA),('AZ',AZ)], nshuf=int(sys.argv[2]))
json.dump(res, open(f'results/hillblind_{tag}.json','w'), indent=1)
ab = [r for r in res if r['above']]
print(f"\n=== {tag} blind Hill: {len(res)} (alphabet,k,P) cells, "
      f"{sum(r['n_rows'] for r in res):,} row-evaluations plus nulls ===")
print(f"cells above their matched ceiling: {len(ab)}")
for r in ab: print("  ", r)
