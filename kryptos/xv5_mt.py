"""XV5 - multiple-testing accounting for frontier item 5."""
import json, numpy as np
R='/home/user/infosecfollow/kryptos/results/'
rng=np.random.default_rng(0)
def emax(N,trials=400000):
    return float(rng.standard_normal((trials,N)).max(axis=1).mean())
print('Expected max of N iid N(0,1):')
for N in (3,6,12,15,16,48,64):
    print(f'  N={N:3d}  E[max]={emax(N):.3f}')

real=json.load(open(R+'wb_dual_real.json'))
az=json.load(open(R+'wb_dual_az.json'))
cells=[r for r in real if r['tag']=='PK10']+az
print(f'\nExecuted real PK10 dual cells: {len(cells)}')
for r in cells:
    print('  alpha=%-2s kmin=%2d mode=%-4s obj=%8.4f qg=%7.4f' %
          (r.get('alpha','KA'),r['kmin'],r['mode'],r['obj'],r['qg']))
per=[r for r in json.load(open(R+'wb_periodic_real.json')) if r['tag']=='PK10']
print(f'Executed real PK10 periodic cells: {len(per)} (3 modes x 16 periods; add==sub identical)')

cap=json.load(open(R+'wb_capacity.json'))
print('\nSearch-space capacity (results/wb_capacity.json):')
for k in ('len>=8','len>=10'):
    print(f"  key vocab {k}: log10(# (pt,key) pairs both word-decomposable and consistent "
          f"with a random 504-letter ciphertext) = {cap['expected_dual_solutions_log10_ptfull'][k]}")
# per-run partial-hypothesis count
print('\nPer beam run: <=100,000 states x 26 letters x up to 4 (pt-cont/pt-restart) x')
print('  (key-cont/key-restart) branches x 504 positions ~= %.1e candidate expansions'
      % (100000*26*2*504))
