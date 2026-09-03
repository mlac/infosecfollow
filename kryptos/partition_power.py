"""Does a constrained class-partition search have any power on item 0a's surviving shape?

probe_partition.py showed the TRUE partition scores well above a random one (z = +2.0 to +12.3).
That is the wrong question.  The right one is §A0's: how many of the partitions the search must
enumerate outscore the truth?  If that number is large the search cannot find the truth no matter
how fast it runs, and the shape is unreachable by this route.

E[# partitions beating the truth] = P(random partition >= truth) x |search space|,
with |search space| = j^p / j! (fixing the block labels), and P estimated from a large null drawn
from the SAME distribution the search enumerates.  This is a matched null by construction.
"""
import numpy as np, json, math
from probe_partition import plant, score

NNULL, NREP = 200_000, 8
rows = []
print(f"{'n':>4s} {'p':>3s} {'j':>2s} {'true':>8s} {'P(rand>=true)':>14s} {'space':>10s} "
      f"{'E[# beating]':>13s}  verdict")
for N in (144, 153, 504):
    for p in (18, 24, 36):
        for j in (3, 4, 5):
            space = j**p / math.factorial(j)
            fr, tr = [], []
            for rep in range(NREP):
                c, a = plant(N, p, j, 700 + 100*rep + p + j)
                t = score(c, p, a, j); tr.append(t)
                r = np.random.default_rng(90000 + rep*13 + p*7 + j)
                A = r.integers(0, j, (NNULL, p))
                s = np.array([score(c, p, A[i], j) for i in range(NNULL)])
                fr.append(float((s >= t).mean()))
            P = float(np.mean(fr)); E = P*space
            # a zero exceedance count only bounds P; report the bound honestly
            bound = '' if P > 0 else f' (P<{1/NNULL:.0e}, so E<{space/NNULL:.1e})'
            rows.append({'n':N,'p':p,'j':j,'true':round(float(np.mean(tr)),5),'P':P,
                         'space':space,'E_beating':E})
            print(f"{N:4d} {p:3d} {j:2d} {np.mean(tr):8.5f} {P:14.2e} {space:10.2e} "
                  f"{E:13.2e}  {'DEAD' if E > 1 else 'live'}{bound}", flush=True)
json.dump({'rows':rows,'nnull':NNULL,'nrep':NREP}, open('results/partition_power.json','w'), indent=1)
print("\nA search can only find the truth when E[# beating] << 1.")
