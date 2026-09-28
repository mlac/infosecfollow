"""Does a constrained class-partition search have any power on item 0a's surviving shape?

probe_partition.py showed the TRUE partition scores well above a random one (z = +2.0 to +12.3).
That is the wrong question.  The right one is §A0's: how many of the partitions the search must
ENUMERATE outscore the truth?  If that number is large the search cannot find the truth however
fast it runs, and the shape is unreachable by this route regardless of compute.

    E[# partitions beating the truth]  =  P(random partition >= truth) x |search space|
    |search space| = j^p / j!   (block labels are interchangeable)

P is estimated from a large null drawn from exactly the distribution the search enumerates, which
makes the null matched to the search by construction rather than by argument.

Vectorised: a partition's group census is a sum of per-class censuses, so score every partition in
a batch with one einsum over the (class -> block) one-hot instead of re-binning the ciphertext.
"""
import numpy as np, json, math, time
from probe_partition import plant

def prep(c, p):
    """per-class letter counts and sizes -- computed once per ciphertext"""
    cnt = np.zeros((p, 26), dtype=np.float32); sz = np.zeros(p, dtype=np.float32)
    for i in range(p):
        idx = np.arange(i, len(c), p)
        cnt[i] = np.bincount(c[idx] % 26, minlength=26); sz[i] = len(idx)
    return cnt, sz

def score_batch(A, cnt, sz, j, chunk=20000):
    """mean IoC over non-empty blocks, for each assignment row of A (nA x p)"""
    out = np.empty(len(A), dtype=np.float64)
    for s in range(0, len(A), chunk):
        B = A[s:s+chunk]
        oh = (B[:, :, None] == np.arange(j)[None, None, :]).astype(np.float32)  # (a,p,j)
        G = np.einsum('apj,pl->ajl', oh, cnt, optimize=True)                    # (a,j,26)
        L = np.einsum('apj,p->aj',   oh, sz,  optimize=True)                    # (a,j)
        num = (G*G).sum(2) - L
        den = L*(L-1)
        ok = den > 0
        io = np.where(ok, num/np.where(ok, den, 1), 0.0)
        out[s:s+chunk] = io.sum(1)/np.maximum(ok.sum(1), 1)
    return out

def true_score(c, p, assign, j):
    cnt, sz = prep(c, p)
    return float(score_batch(assign[None, :], cnt, sz, j)[0])

if __name__ == '__main__':
    NNULL, NREP = 200_000, 8
    rows = []; t0 = time.time()
    print(f"{'n':>4s} {'p':>3s} {'j':>2s} {'true':>8s} {'null max':>9s} {'P(rand>=true)':>14s} "
          f"{'space':>10s} {'E[# beating]':>13s}  verdict", flush=True)
    for N in (144, 153, 504):
        for p in (18, 24, 36):
            for j in (3, 4, 5):
                space = j**p / math.factorial(j)
                fr, tr, nmax = [], [], []
                for rep in range(NREP):
                    c, a = plant(N, p, j, 700 + 100*rep + p + j)
                    cnt, sz = prep(c, p)
                    t = float(score_batch(a[None, :], cnt, sz, j)[0]); tr.append(t)
                    r = np.random.default_rng(90000 + rep*13 + p*7 + j)
                    s = score_batch(r.integers(0, j, (NNULL, p)), cnt, sz, j)
                    fr.append(float((s >= t).mean())); nmax.append(float(s.max()))
                P = float(np.mean(fr)); E = P*space
                bound = '' if P > 0 else f'  (P<{1/NNULL:.0e}: E<{space/NNULL:.1e})'
                rows.append({'n':N,'p':p,'j':j,'true':round(float(np.mean(tr)),5),
                             'null_max':round(float(np.mean(nmax)),5),'P':P,'space':space,
                             'E_beating':E,'dead':bool(E > 1)})
                print(f"{N:4d} {p:3d} {j:2d} {np.mean(tr):8.5f} {np.mean(nmax):9.5f} {P:14.2e} "
                      f"{space:10.2e} {E:13.2e}  {'DEAD' if E > 1 else 'live'}{bound}", flush=True)
    json.dump({'rows':rows,'nnull':NNULL,'nrep':NREP,'wall':round(time.time()-t0,1)},
              open('results/partition_power.json','w'), indent=1)
    print(f"\nA search finds the truth only when E[# beating] << 1.   {time.time()-t0:.0f}s")
