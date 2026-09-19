"""Autopsy the 87 'above ceiling' cells from run_smallmod.py.

The sweep used only FOUR shuffle-nulls per cell, so its ceiling is the max of 4 draws, which the
observation exceeds 1 time in 5 under the null.  Across 408 cells that predicts 81.6 crossings; 87
were seen (z = +0.67).  The count is therefore already explained by the null.

But the doctrine says autopsy anything at or above a ceiling, so the arithmetic is not enough on its
own: re-run the top-ranked cells against a properly sized matched null (the identical search on
letter-shuffles of the same ciphertext, hundreds of draws instead of four) and report where the
observation actually falls.  This is the same escalation that killed the PK8 p=7 flag in §C1.
"""
import numpy as np, json, time
from smallmod import run_cell
from lib import KA, AZ, CT, to_idx

DS = [d for d in range(1, 26) if np.gcd(d, 26) == 1]
CELLS = [   # the eight largest deltas from the sweep
    ('pk9','AZ',8,3,'lag1'), ('pk8','AZ',6,5,'lag1'), ('pk8','AZ',8,5,'lag1'),
    ('pk8','AZ',4,3,'aca'),  ('pk8','AZ',8,6,'lag1'), ('pk9','AZ',3,6,'lag1'),
    ('pk8','AZ',5,8,'aca'),  ('pk8','KA',8,3,'lag1'),
]
ALPHA = {'KA': KA, 'AZ': AZ}
rng = np.random.default_rng(20260903)
t0 = time.time(); out = []
print(f"{'target':7s} {'al':3s} {'m':>2s} {'L':>2s} {'rec':5s} {'obs':>8s} {'nulls':>6s} "
      f"{'null mean':>10s} {'sd':>7s} {'null max':>9s} {'z':>7s} {'p_emp':>8s}  verdict", flush=True)
for tag, an, m, L, rec in CELLS:
    ct = CT[tag]; n = len(ct); al = ALPHA[an]
    ncfg = m**L * len(DS)
    NN = 500 if ncfg < 200_000 else (150 if ncfg < 2_000_000 else 60)   # budget by cell cost
    C = to_idx(ct, al).astype(np.int64)
    (obs, d, p), _ = run_cell(C, m, L, rec, DS, n)
    nulls = []
    for i in range(NN):
        Cx = to_idx(''.join(rng.permutation(list(ct))), al).astype(np.int64)
        nulls.append(run_cell(Cx, m, L, rec, DS, n)[0][0])
    nl = np.array(nulls)
    z = (obs - nl.mean())/nl.std(); pe = float((nl >= obs).mean())
    above = obs > nl.max()
    out.append({'target':tag,'alpha':an,'m':m,'L':L,'rec':rec,'obs':round(float(obs),5),
                'n_nulls':NN,'null_mean':round(float(nl.mean()),5),'null_sd':round(float(nl.std()),5),
                'null_max':round(float(nl.max()),5),'z':round(float(z),2),'p_emp':pe,'above':bool(above),
                'd':d,'primer':list(p),'n_configs_per_run':ncfg})
    print(f"{tag:7s} {an:3s} {m:2d} {L:2d} {rec:5s} {obs:8.5f} {NN:6d} {nl.mean():10.5f} "
          f"{nl.std():7.5f} {nl.max():9.5f} {z:+7.2f} {pe:8.4f}  "
          f"{'*** STILL ABOVE ***' if above else 'killed'}", flush=True)
    json.dump({'cells':out,'wall':round(time.time()-t0,1)},
              open('results/smallmod_autopsy.json','w'), indent=1)
print(f"\n  cells still above a properly sized ceiling: {sum(c['above'] for c in out)} of {len(out)}"
      f"   ({time.time()-t0:.0f}s)", flush=True)
