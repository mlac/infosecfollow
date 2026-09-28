"""The strongest form of the class-partition attack: likelihood, not IoC.

§G8 (unbalanced) and its balanced variant both score a partition by the mean IoC of its merged
groups.  IoC only measures concentration; it throws away WHICH letters are frequent.  Under the
hypothesis each merged group is English read through the KRYPTOS alphabet and shifted by one unknown
amount, so the sharper statistic is

    score(partition) = sum over groups of  max over shift of  log P(group census | shifted English)

which is the log-likelihood a real solver would maximise.  Both the true partition and every null
partition are scored the same way, and the shift maximisation is inside both, so the multiplicity is
matched.  Combined with the balanced constraint this is the best version of the attack I can build;
if the truth still loses, the shape is unreachable by partition search rather than by a weak choice
of statistic.

Reference letter distribution: the setter's own seven plaintexts, in KA index space.
"""
import numpy as np, json, math, time
from partition_power import prep
from partition_balanced import balanced, plant_balanced
from lib import KA, PT, to_idx

_pt = ''.join(PT.values())
_f  = np.bincount(to_idx(_pt, KA), minlength=26).astype(np.float64) + 0.5   # Laplace: the
ENG = _f/_f.sum()   # setter's 1,912 letters leave some rare letters at zero count
# LOGE[s, x] = log P(plaintext letter | ciphertext index x under shift s)
LOGE = np.array([[math.log(ENG[(x - s) % 26]) for x in range(26)] for s in range(26)])

def score_llr(A, cnt, j, chunk=20000):
    """sum over groups of the best-shift log-likelihood, per assignment row"""
    out = np.empty(len(A), dtype=np.float64)
    for s in range(0, len(A), chunk):
        B  = A[s:s+chunk]
        oh = (B[:, :, None] == np.arange(j)[None, None, :]).astype(np.float32)
        G  = np.einsum('apj,pl->ajl', oh, cnt, optimize=True)      # (a, j, 26) group censuses
        out[s:s+chunk] = (G @ LOGE.T).max(2).sum(1)                # best shift per group, summed
    return out

if __name__ == '__main__':
    NNULL, NREP = 60_000, 10
    rows = []; t0 = time.time()
    print(f"{'n':>4s} {'p':>3s} {'j':>2s} {'true':>10s} {'null mean':>10s} {'null max':>10s} "
          f"{'P(rand>=true)':>14s} {'space':>10s} {'E[# beating]':>13s}  verdict", flush=True)
    for N in (144, 153, 504):
        for p, j in ((18,3), (24,3), (36,3), (24,4), (36,4), (36,6)):
            space = math.factorial(p)/(math.factorial(p//j)**j)/math.factorial(j)
            fr, tr, nmx, nmn = [], [], [], []
            for rep in range(NREP):
                c, a = plant_balanced(N, p, j, 31337 + rep*7 + p*3 + j)
                cnt, _ = prep(c, p)
                t = float(score_llr(a[None, :], cnt, j)[0]); tr.append(t)
                s = score_llr(balanced(np.random.default_rng(5000+rep*11+p+j), p, j, NNULL), cnt, j)
                fr.append(float((s >= t).mean())); nmx.append(float(s.max())); nmn.append(float(s.mean()))
            P = float(np.mean(fr)); E = P*space
            bound = '' if P > 0 else f'  (P<{1/NNULL:.0e}: E<{space/NNULL:.1e})'
            rows.append({'n':N,'p':p,'j':j,'true':round(float(np.mean(tr)),3),
                         'null_mean':round(float(np.mean(nmn)),3),
                         'null_max':round(float(np.mean(nmx)),3),'P':P,'space':space,
                         'E_beating':E,'dead':bool(E > 1)})
            print(f"{N:4d} {p:3d} {j:2d} {np.mean(tr):10.2f} {np.mean(nmn):10.2f} {np.mean(nmx):10.2f} "
                  f"{P:14.2e} {space:10.2e} {E:13.2e}  {'DEAD' if E > 1 else 'LIVE'}{bound}", flush=True)
    json.dump({'rows':rows,'nnull':NNULL,'nrep':NREP,'wall':round(time.time()-t0,1)},
              open('results/partition_llr.json','w'), indent=1)
    print(f"\n{time.time()-t0:.0f}s", flush=True)
