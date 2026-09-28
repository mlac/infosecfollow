"""Exhaustive UNBALANCED enumeration -- removes §G8's equal-usage assumption.

§G8's attack assumes the key's j letters are used equally often (6/6/6 classes at p=18).  A real key
need not be: an 8/6/4 split escapes it entirely.  Dropping that assumption means enumerating every
assignment of 18 classes to 3 blocks, not just the balanced ones.

Counting, with the 3! label symmetry removed by fixing class 0 to block 0 and requiring the first
class not in block 0 to be in block 1:

    sum over k=1..17 of 3^(17-k)  +  1  =  (3^17 - 1)/2 + 1  =  64,570,082

which is S(18,1) + S(18,2) + S(18,3) exactly -- 23x the balanced space, and 1.16 GB if materialised,
so it is generated and scored in chunks instead.  A sampled null cannot resolve this: 200,000 draws
only bound E < 320.  Only the full enumeration answers it.
"""
import numpy as np, itertools, time

def gen_canonical(p=18, j=3, chunk=2_000_000):
    """yield chunks of every assignment of p classes to j blocks, label symmetry removed.
    class 0 is in block 0; the first class not in block 0 is in block 1."""
    yield np.zeros((1, p), dtype=np.int8)                     # everything in one block
    for k in range(1, p):                                      # k = first class outside block 0
        tail = p - k - 1
        total = j**tail if tail else 1
        for s in range(0, total, chunk):
            m = min(chunk, total - s)
            A = np.zeros((m, p), dtype=np.int8)
            A[:, k] = 1
            if tail:
                idx = np.arange(s, s+m, dtype=np.int64)
                for t in range(tail):                          # base-j digits of the free tail
                    A[:, p-1-t] = (idx // (j**t)) % j
            yield A

def count(p=18, j=3):
    return sum(len(a) for a in gen_canonical(p, j))

if __name__ == '__main__':
    import sys, json
    from lib import KA, AZ, CT, to_idx
    from partition_power import prep
    from partition_llr import score_llr

    P, J, NNULL = 18, 3, 10
    targets = sys.argv[1:] or ['pk9']
    rng = np.random.default_rng(777)

    def best(C):
        cnt, _ = prep(C, P); b = -1e18; n = 0
        for A in gen_canonical(P, J):
            s = score_llr(A.astype(np.int64), cnt, J); n += len(A)
            m = float(s.max())
            if m > b: b = m
        return b, n

    t0 = time.time(); out = []
    for tag in targets:
        ct = CT[tag]
        for an, al in (('KA', KA), ('AZ', AZ)):
            C = to_idx(ct, al).astype(np.int64)
            obs, ncfg = best(C)
            print(f"  {tag} {an}: observed {obs:.2f} over {ncfg:,} partitions "
                  f"({time.time()-t0:.0f}s)", flush=True)
            nulls = []
            for i in range(NNULL):
                Cx = to_idx(''.join(rng.permutation(list(ct))), al).astype(np.int64)
                nulls.append(best(Cx)[0])
                print(f"    null {i+1}/{NNULL}: {nulls[-1]:.2f} ({time.time()-t0:.0f}s)", flush=True)
            nm, nsd, nmx = float(np.mean(nulls)), float(np.std(nulls)), float(np.max(nulls))
            z = (obs-nm)/nsd if nsd else 0.0
            out.append({'target': tag, 'alpha': an, 'p': P, 'j': J, 'obs': round(obs, 3),
                        'null_mean': round(nm, 3), 'null_sd': round(nsd, 3),
                        'null_max': round(nmx, 3), 'z': round(z, 2), 'above': obs > nmx,
                        'n_partitions': ncfg})
            print(f"  => {tag} {an}: obs {obs:.2f}  null {nm:.2f} +- {nsd:.2f}  max {nmx:.2f}  "
                  f"z {z:+.2f}  {'*** ABOVE CEILING ***' if obs > nmx else ''}", flush=True)
            json.dump({'cells': out, 'nnull': NNULL, 'wall': round(time.time()-t0, 1)},
                      open('results/partition_unbal.json', 'w'), indent=1)
