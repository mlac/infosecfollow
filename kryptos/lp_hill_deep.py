"""Restart-budget robustness check: re-run scorer (b) at 6x the restart budget on the
top-ranked periods for PK8/PK9, so the negative cannot be blamed on under-search.
Also runs a synthetic period-p positive control at the SAME length and SAME budget.
"""
import numpy as np, sys, json, time
sys.path.insert(0, '.')
from lib import CT, PT, KA, AZ, AZI
from lp_hill import climb, cidx, PERM, decrypt

R = int(sys.argv[1]) if len(sys.argv) > 1 else 240
NN = int(sys.argv[2]) if len(sys.argv) > 2 else 10
rng = np.random.default_rng(555)
ENG = np.array([AZI[c] for c in ''.join(PT[k] for k in PT)], dtype=np.int64)
CAND = json.load(open('results/lp_hill_deep_targets.json'))
out = {}; t0 = time.time()
for name, alpha, P in CAND:
    C = cidx(CT[name], alpha)
    obs, K = climb(C, P, PERM[alpha], rng, R)
    nl = np.array([climb(rng.permutation(C), P, PERM[alpha], rng, R)[0] for _ in range(NN)])
    z = (obs - nl.mean())/(nl.std()+1e-12)
    pt = decrypt(C, K, KA if alpha == 'KA' else AZ)
    # matched synthetic positive control: same n, same P, same budget
    n = len(C); st = rng.integers(0, len(ENG)-n)
    t = ENG[st:st+n]; kk = rng.integers(0, 26, size=P)
    S = (t + kk[np.arange(n) % P]) % 26
    so, sK = climb(S, P, PERM['AZ'], rng, R)
    sn = np.array([climb(rng.permutation(S), P, PERM['AZ'], rng, R)[0] for _ in range(NN)])
    sz = (so - sn.mean())/(sn.std()+1e-12)
    sd_ = ''.join(AZ[int(v)] for v in (S - sK[np.arange(n) % P]) % 26)
    acc = sum(a == b for a, b in zip(sd_, ''.join(AZ[int(v)] for v in t)))/n
    out[f"{name}_{alpha}_{P}"] = dict(obs=float(obs), null_mean=float(nl.mean()),
        null_max=float(nl.max()), z=float(z), above_null_max=bool(obs > nl.max()), pt=pt,
        synth_z=float(sz), synth_letter_accuracy=round(acc, 3), restarts=R, nnull=NN)
    print(f"{name}/{alpha} p={P} R={R}: obs={obs:.4f} nullmax={nl.max():.4f} z={z:+.2f}"
          f"{'  ABOVE-NULLMAX' if obs > nl.max() else ''} || SYNTH same n,P,R: z={sz:+.2f} "
          f"letters-correct={acc:.2f}  [{time.time()-t0:.0f}s]", flush=True)
    print(f"    {pt[:76]}", flush=True)
    json.dump(out, open('results/lp_hill_deep.json', 'w'), indent=1)
