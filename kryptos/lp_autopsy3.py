"""Doctrine-4 autopsy of the two cells that survived a 60-shuffle null at R=240:
   pk8/KA p=72 (z=+2.47) and pk9/AZ p=42 (z=+3.38).

Discriminator: is the elevation PERIOD-SPECIFIC (a real period-p key) or GENERIC
(hill-climbing real cipher text always beats hill-climbing shuffled text, because real
ciphertext retains non-uniform local structure that a shuffle destroys)?

Two arms, all cells at the SAME budget so they are directly comparable:
  A) NEIGHBOUR PERIODS on the same target. A real period-p key elevates p and its
     multiples only; a generic effect elevates every long period equally.
  B) NEGATIVE CONTROLS: SOLVED ciphertexts (PK1 period-10, PK2 pure columnar, PK5 running
     key, PK6 period-6 + double columnar, PK7 Hill) truncated to the same length. These
     provably have NO period 25-72 key. If they light up too, the effect is generic.
"""
import numpy as np, sys, json, time
sys.path.insert(0,'.')
from lib import CT, KA, AZ
from lp_hill import climb, cidx, PERM, decrypt
R, NN = 120, 40
rng = np.random.default_rng(808)
CASES = ([('pk8', CT['pk8'], 'KA', p) for p in (68, 69, 70, 71, 72)] +
         [('pk9', CT['pk9'], 'AZ', p) for p in (41, 42, 43)] +
         [('NEGpk1', CT['pk1'][:153], 'KA', 72), ('NEGpk6', CT['pk6'][:153], 'KA', 72),
          ('NEGpk7', CT['pk7'][:153], 'KA', 72), ('NEGpk2', CT['pk2'][:144], 'AZ', 42),
          ('NEGpk5', CT['pk5'][:144], 'AZ', 42), ('NEGpk7b', CT['pk7'][:144], 'AZ', 42)])
out = {}; t0 = time.time()
for name, ct, alpha, P in CASES:
    C = cidx(ct, alpha)
    obs, K = climb(C, P, PERM[alpha], rng, R)
    nl = np.array([climb(rng.permutation(C), P, PERM[alpha], rng, R)[0] for _ in range(NN)])
    z = float((obs - nl.mean())/nl.std()); pe = float((nl >= obs).mean())
    key = f"{name}_{alpha}_p{P}"
    out[key] = dict(obs=float(obs), null_mean=float(nl.mean()), null_sd=float(nl.std()),
                    null_max=float(nl.max()), z=z, p_emp=pe,
                    above_null_max=bool(obs > nl.max()), restarts=R, nnull=NN,
                    letters_per_key_slot=round(len(C)/P, 2),
                    pt=decrypt(C, K, KA if alpha == 'KA' else AZ))
    print(f"{key:16s} z={z:+6.2f} p_emp={pe:.3f} aboveNullMax={str(obs > nl.max()):5s} "
          f"slots={len(C)/P:.2f}  [{time.time()-t0:.0f}s]", flush=True)
    json.dump(out, open('results/lp_autopsy3.json', 'w'), indent=1)
