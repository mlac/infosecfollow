"""Exhaustive enumeration of balanced class-partitions, scored by likelihood.

The balanced space for p=18 classes into j=3 blocks of 6 is exactly

    C(17,5) x C(11,5) = 6188 x 462 = 2,858,856

after fixing class 0 to block 0 and the smallest remaining class to block 1, which kills the 3!
label symmetry.  That is small enough to enumerate outright, so the question "does the truth win?"
gets an exact answer instead of a tail extrapolation.

This is aimed at frontier item 0a's second surviving shape on PK9 -- a key of period >= 18 built
from only 3-5 distinct letters -- which §G7 showed the census does not screen and §F15 showed the
residue battery cannot see.  p=18 is the smallest period in that shape and the only one whose
balanced space is enumerable; the scope is stated, not glossed.
"""
import numpy as np, itertools, math
from partition_power import prep
from partition_llr import score_llr
from partition_balanced import plant_balanced

def enum_balanced(p=18, j=3):
    """every balanced assignment, label symmetry removed; returns (space, p) int8"""
    assert p % j == 0
    k = p//j
    rest0 = list(range(1, p))
    rows = []
    for b0 in itertools.combinations(rest0, k-1):            # class 0 is always in block 0
        blk0 = (0,) + b0
        left = [x for x in range(p) if x not in blk0]
        if j == 2:
            rows.append((blk0, tuple(left))); continue
        for b1 in itertools.combinations(left[1:], k-1):     # smallest leftover fixes block 1
            blk1 = (left[0],) + b1
            rows.append((blk0, blk1, tuple(x for x in left if x not in blk1)))
    A = np.empty((len(rows), p), dtype=np.int64)
    for i, blocks in enumerate(rows):
        for b, cls in enumerate(blocks):
            for x in cls: A[i, x] = b
    return A

def canon(a, j):
    """canonical labelling so a recovered assignment can be compared to the truth"""
    seen, m, nxt = {}, np.empty_like(a), 0
    for i, v in enumerate(a):
        if v not in seen: seen[v] = nxt; nxt += 1
        m[i] = seen[v]
    return tuple(m.tolist())

if __name__ == '__main__':
    import time, json, sys
    P, J = 18, 3
    t0 = time.time(); A = enum_balanced(P, J)
    print(f"enumerated {len(A):,} balanced partitions of {P} classes into {J} blocks "
          f"({time.time()-t0:.1f}s); expected {math.comb(17,5)*math.comb(11,5):,}", flush=True)
    NREP = 20
    print(f"\nPOWER: does the true partition win the full enumeration?", flush=True)
    print(f"  {'n':>4s} {'rank':>8s} {'of':>10s} {'true':>10s} {'best':>10s} {'margin':>8s} "
          f"{'exact match':>12s}", flush=True)
    res = {}
    for N in (144, 153, 504):
        ranks, exact = [], []
        for rep in range(NREP):
            c, a = plant_balanced(N, P, J, 31337 + rep*7 + P*3 + J)
            cnt, _ = prep(c, P)
            s = score_llr(A, cnt, J)
            t = float(score_llr(a[None, :], cnt, J)[0])
            r = int((s > t).sum()) + 1
            ranks.append(r); exact.append(canon(A[int(s.argmax())], J) == canon(a, J))
            if rep == 0:
                print(f"  {N:4d} {r:8,d} {len(A):10,d} {t:10.2f} {s.max():10.2f} "
                      f"{t-s.max():8.2f} {str(exact[-1]):>12s}", flush=True)
        res[N] = {'rank_median': float(np.median(ranks)), 'rank_best': int(min(ranks)),
                  'exact_rate': float(np.mean(exact)), 'n_rep': NREP, 'space': len(A)}
        print(f"  -> n={N}: exact recovery {np.mean(exact)*100:.0f}% of {NREP} plants, "
              f"median rank {np.median(ranks):,.0f} of {len(A):,}", flush=True)
    json.dump(res, open('results/partition_enum_power.json','w'), indent=1)
    print(f"\n{time.time()-t0:.0f}s", flush=True)
