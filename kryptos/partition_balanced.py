"""The obvious rescue for §G8: constrain the partition to be BALANCED.

In the unconstrained search a random partition can beat the truth by being lopsided -- a block
holding two classes is a 16-letter group whose IoC is high by chance.  That inflation is an artifact
of block-size variance, not evidence about the key, and it is removable: if the key of period p uses
its j letters roughly equally, the true partition is near-balanced, so restrict the search to
partitions with exactly p/j classes per block.  That shrinks the space AND removes the artifact.

  p=18, j=3:  multinomial(18;6,6,6)/3! = 2,858,856  -- small enough to enumerate outright

The true key is re-planted balanced here too, so hypothesis and search match exactly.  If the truth
wins, item 0a's second shape is attackable after all and this is the attack.
"""
import numpy as np, json, math, time
from partition_power import prep, score_batch
from lib import KA, PT, to_idx, col_enc

SRC = ''.join(PT[k] for k in ('pk2','pk3','pk5','pk6','pk7','pk4','pk1'))

def balanced(rng, p, j, n):
    """n uniform random balanced assignments, vectorised: argsort of uniform noise gives n
    independent uniform permutations at once, and the block labels ride along."""
    order  = np.argsort(rng.random((n, p)), axis=1)
    blocks = np.broadcast_to(np.repeat(np.arange(j), p//j), (n, p))
    A = np.empty((n, p), dtype=np.int64)
    np.put_along_axis(A, order, blocks, axis=1)
    return A

def plant_balanced(N, p, j, seed, W=9):
    r = np.random.default_rng(seed)
    a = balanced(r, p, j, 1)[0]
    S = r.permutation(26)[:j]
    off = int(r.integers(0, len(SRC)-N))
    x = to_idx(col_enc(SRC[off:off+N], list(r.permutation(W))), KA).astype(np.int64)
    return (x + np.resize(S[a], N)) % 26, a

if __name__ == '__main__':
    NNULL, NREP = 60_000, 10
    rows = []; t0 = time.time()
    print(f"{'n':>4s} {'p':>3s} {'j':>2s} {'true':>8s} {'null mean':>10s} {'null max':>9s} "
          f"{'P(rand>=true)':>14s} {'space':>10s} {'E[# beating]':>13s}  verdict", flush=True)
    for N in (144, 153, 504):
        for p, j in ((18,3), (24,3), (36,3), (24,4), (36,4), (36,6)):
            space = math.factorial(p)/(math.factorial(p//j)**j)/math.factorial(j)
            fr, tr, nmx, nmn = [], [], [], []
            for rep in range(NREP):
                c, a = plant_balanced(N, p, j, 31337 + rep*7 + p*3 + j)
                cnt, sz = prep(c, p)
                t = float(score_batch(a[None, :], cnt, sz, j)[0]); tr.append(t)
                s = score_batch(balanced(np.random.default_rng(5000+rep*11+p+j), p, j, NNULL),
                                cnt, sz, j)
                fr.append(float((s >= t).mean())); nmx.append(float(s.max())); nmn.append(float(s.mean()))
            P = float(np.mean(fr)); E = P*space
            bound = '' if P > 0 else f'  (P<{1/NNULL:.0e}: E<{space/NNULL:.1e})'
            rows.append({'n':N,'p':p,'j':j,'true':round(float(np.mean(tr)),5),
                         'null_mean':round(float(np.mean(nmn)),5),
                         'null_max':round(float(np.mean(nmx)),5),'P':P,'space':space,
                         'E_beating':E,'dead':bool(E > 1)})
            print(f"{N:4d} {p:3d} {j:2d} {np.mean(tr):8.5f} {np.mean(nmn):10.5f} {np.mean(nmx):9.5f} "
                  f"{P:14.2e} {space:10.2e} {E:13.2e}  {'DEAD' if E > 1 else 'LIVE'}{bound}", flush=True)
    json.dump({'rows':rows,'nnull':NNULL,'nrep':NREP,'wall':round(time.time()-t0,1)},
              open('results/partition_balanced.json','w'), indent=1)
    print(f"\n{time.time()-t0:.0f}s", flush=True)
