"""Autopsy of the cells flagged ABOVE-NULLMAX in the R=240 deep check, with a 60-shuffle
matched null at the SAME R=240 budget (the deep check used only 10)."""
import numpy as np, sys, json, time
sys.path.insert(0,'.')
from lib import CT, KA, AZ
from lp_hill import climb, cidx, PERM, decrypt
rng = np.random.default_rng(2024)
CASES=[('pk9','AZ',42,1,240),('pk8','KA',35,1,240),('pk8','KA',72,1,240)]
out={}; t0=time.time()
for name,alpha,P,sign,R in CASES:
    C=cidx(CT[name],alpha)
    obs,K=climb(C,P,PERM[alpha],rng,R,sign=sign)
    nl=np.array([climb(rng.permutation(C),P,PERM[alpha],rng,R,sign=sign)[0] for _ in range(60)])
    key=f"{name}_{alpha}_p{P}_R{R}"
    out[key]=dict(obs=float(obs),null_mean=float(nl.mean()),null_sd=float(nl.std()),
                  null_max=float(nl.max()),z=float((obs-nl.mean())/nl.std()),
                  p_emp_60=float((nl>=obs).mean()),above_null_max_60=bool(obs>nl.max()),
                  nnull=60,restarts=R,letters_per_key_slot=round(len(C)/P,2),
                  pt=decrypt(C,K,KA if alpha=='KA' else AZ,sign=sign))
    print(f"{key}: obs={obs:.4f} nullmu={nl.mean():.4f} sd={nl.std():.4f} max={nl.max():.4f} "
          f"z={(obs-nl.mean())/nl.std():+.2f} p_emp(60)={float((nl>=obs).mean()):.4f} "
          f"above60max={obs>nl.max()}  [{time.time()-t0:.0f}s]", flush=True)
    print('   ', out[key]['pt'][:90], flush=True)
    json.dump(out, open('results/lp_autopsy2.json','w'), indent=1)
