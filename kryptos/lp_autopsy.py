"""Targeted autopsy: the three cells that beat their 12-shuffle per-period null max.
Re-run each with a 120-shuffle matched null at the identical restart budget, plus the
family-wise ceiling from the same 120 shuffles scanned over all 48 periods is too costly,
so we report the exact per-period empirical p-value at 120 nulls."""
import numpy as np, sys, json, time
sys.path.insert(0,'.')
from lib import CT, KA, AZ
from lp_hill import climb, cidx, PERM, decrypt
rng = np.random.default_rng(31337)
CASES = [('pk9','AZ',63,-1),('pk9','KA',38,-1),('pk8','KA',30,-1),('pk8','KA',72,1)]
out={}; t0=time.time()
for name,alpha,P,sign in CASES:
    C = cidx(CT[name], alpha)
    obs,K = climb(C,P,PERM[alpha],rng,40,sign=sign)
    nl = np.array([climb(rng.permutation(C),P,PERM[alpha],rng,40,sign=sign)[0] for _ in range(120)])
    pe = float((nl>=obs).mean())
    key=f"{name}_{alpha}_p{P}_{'beau' if sign<0 else 'sub'}"
    out[key]=dict(obs=float(obs), null_mean=float(nl.mean()), null_sd=float(nl.std()),
                  null_max=float(nl.max()), z=float((obs-nl.mean())/nl.std()),
                  p_emp_120=pe, above_null_max_120=bool(obs>nl.max()),
                  letters_per_key_slot=round(len(C)/P,2), pt=decrypt(C,K,KA if alpha=='KA' else AZ,sign=sign))
    print(f"{key}: obs={obs:.4f} null mu={nl.mean():.4f} sd={nl.std():.4f} max={nl.max():.4f} "
          f"z={(obs-nl.mean())/nl.std():+.2f} p_emp(120)={pe:.4f} "
          f"above120max={obs>nl.max()} letters/slot={len(C)/P:.2f}  [{time.time()-t0:.0f}s]", flush=True)
    json.dump(out, open('results/lp_autopsy.json','w'), indent=1)
