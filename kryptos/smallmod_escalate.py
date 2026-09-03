"""Full escalation of the one sweep cell that survived a properly sized null.

pk8 / plain A-Z / m=8, L=6, lag-1 recurrence: obs 0.05573 against a 60-shuffle null max of 0.05538
(mean 0.05275, sd 0.00099, z=+3.00).  It survived only a 60-draw ceiling, and 60 was chosen because
the cell costs 8^6 x 12 = 3.1M configurations per run.  P(obs > max of 60) = 1/61 = 0.016 under the
null, so across the sweep's 408 cells roughly 6.7 such survivors are expected by chance -- but that
argument is arithmetic, and the doctrine wants the search re-run, not reasoned about.

Four independent attacks on the flag, the same pattern that killed the Gromark flag three ways:
  1. a much larger matched null (400 shuffles, fresh seed) -- does it survive its own ceiling?
  2. replication on an INDEPENDENT shuffle bank -- is the effect reproducible or was it one draw?
  3. neighbouring cells (m=8 L=5,7; m=7,9 L=6; and the ACA recurrence at m=8 L=6) -- a real
     recurrence elevates its neighbours; an isolated spike is noise.
  4. the decrypt and the recovered primer -- letter-stacking shows up in the profile, as in §C1/§G8.
"""
import numpy as np, json, time
from smallmod import run_cell
from lib import AZ, CT, to_idx, to_str, ioc

DS = [d for d in range(1, 26) if np.gcd(d, 26) == 1]
TAG, M, L, REC = 'pk8', 8, 6, 'lag1'
ct = CT[TAG]; n = len(ct)
C = to_idx(ct, AZ).astype(np.int64)
t0 = time.time(); res = {}

(obs, d, primer), ncfg = run_cell(C, M, L, REC, DS, n)
print(f"cell {TAG} AZ m={M} L={L} {REC}: obs {obs:.5f}, d={d}, primer={primer}, "
      f"{ncfg:,} configs/run ({time.time()-t0:.0f}s for one run)", flush=True)

# 4. profile and decrypt first -- cheap, and often decisive on its own
k = np.zeros(n, dtype=np.int64); k[:L] = primer[:L]
for i in range(L, n): k[i] = (k[i-L] + k[i-1]) % M
pt = (C - d*k) % 26
txt = to_str(pt, AZ)
prof = np.sort(np.bincount(pt, minlength=26)/n)[::-1][:6]
print(f"  decrypt IoC {ioc(txt):.5f}   top-6 freqs {np.round(prof,3).tolist()}")
print(f"  English top-6 for comparison  [0.127, 0.091, 0.082, 0.075, 0.070, 0.067]")
print(f"  decrypt: {txt}", flush=True)
res['obs'] = round(float(obs), 5); res['d'] = int(d); res['primer'] = list(primer)
res['decrypt'] = txt; res['decrypt_ioc'] = round(float(ioc(txt)), 5)
res['profile_top6'] = [round(float(x), 4) for x in prof]

# 1 + 2. a large matched null, split into two independent halves for replication
NN = 400
rng = np.random.default_rng(31415)
nulls = []
for i in range(NN):
    Cx = to_idx(''.join(rng.permutation(list(ct))), AZ).astype(np.int64)
    nulls.append(run_cell(Cx, M, L, REC, DS, n)[0][0])
    if (i+1) % 50 == 0:
        a = np.array(nulls)
        print(f"    null {i+1}/{NN}: mean {a.mean():.5f} max {a.max():.5f} "
              f"obs_above={obs > a.max()} ({time.time()-t0:.0f}s)", flush=True)
        json.dump(res | {'nulls_so_far': i+1, 'null_mean': round(float(a.mean()), 5),
                         'null_max': round(float(a.max()), 5),
                         'above': bool(obs > a.max())},
                  open('results/smallmod_escalate.json', 'w'), indent=1)
a = np.array(nulls); h1, h2 = a[:NN//2], a[NN//2:]
res.update({'n_nulls': NN, 'null_mean': round(float(a.mean()), 5),
            'null_sd': round(float(a.std()), 5), 'null_max': round(float(a.max()), 5),
            'z': round(float((obs-a.mean())/a.std()), 2), 'p_emp': float((a >= obs).mean()),
            'above': bool(obs > a.max()),
            'half1_max': round(float(h1.max()), 5), 'half2_max': round(float(h2.max()), 5),
            'above_half1': bool(obs > h1.max()), 'above_half2': bool(obs > h2.max())})
print(f"\n  {NN}-shuffle matched null: mean {a.mean():.5f} sd {a.std():.5f} max {a.max():.5f}")
print(f"  obs {obs:.5f}  z {(obs-a.mean())/a.std():+.2f}  p_emp {(a>=obs).mean():.4f}  "
      f"{'*** STILL ABOVE ***' if obs > a.max() else 'KILLED'}")
print(f"  replication on independent halves: above half-1 {obs > h1.max()} "
      f"(max {h1.max():.5f}), above half-2 {obs > h2.max()} (max {h2.max():.5f})", flush=True)

# 3. neighbours
print(f"\n  neighbouring cells (a real recurrence elevates these too):", flush=True)
NB = [(8,5,'lag1'), (8,7,'lag1'), (7,6,'lag1'), (9,6,'lag1'), (8,6,'aca')]
nb = []
for m2, l2, r2 in NB:
    (o2, _, _), _ = run_cell(C, m2, l2, r2, DS, n)
    ns = []
    for i in range(40):
        Cx = to_idx(''.join(rng.permutation(list(ct))), AZ).astype(np.int64)
        ns.append(run_cell(Cx, m2, l2, r2, DS, n)[0][0])
    v = np.array(ns); z2 = (o2-v.mean())/v.std()
    nb.append({'m':m2,'L':l2,'rec':r2,'obs':round(float(o2),5),'z':round(float(z2),2),
               'above':bool(o2 > v.max())})
    print(f"    m={m2} L={l2} {r2:5s}: obs {o2:.5f}  40-null mean {v.mean():.5f} "
          f"max {v.max():.5f}  z {z2:+.2f}  {'above' if o2>v.max() else 'below'}", flush=True)
res['neighbours'] = nb
json.dump(res, open('results/smallmod_escalate.json', 'w'), indent=1)
print(f"\n  total {time.time()-t0:.0f}s", flush=True)
