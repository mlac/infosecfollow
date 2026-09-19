"""Autopsy of the PK8 p=18 j=3 cell, which landed 0.16 nats BELOW its ceiling -- effectively tied.

Standing doctrine: autopsy anything at or above the ceiling.  obs -495.54 against a null max of
-495.38 is not above it, but the gap is 0.16 nats on a scale where the truth beats the runner-up by
14, so it is a tie and gets the same treatment: recover the winning partition, decrypt under it,
show the result, and state what multiplicity predicts.

The attack assumes a columnar may sit underneath, so a genuine hit need NOT read as English here --
it would read as English only after the transposition is undone.  What a genuine hit must show is a
group-wise letter profile close to English.  That is the thing to look at.
"""
import numpy as np
from lib import KA, CT, to_idx, to_str, ioc
from partition_power import prep
from partition_llr import score_llr, ENG, LOGE
from partition_enum import enum_balanced

P, J, TAG, ALPHA = 18, 3, 'pk8', KA
C = to_idx(CT[TAG], ALPHA).astype(np.int64); n = len(C)
A = enum_balanced(P, J)
cnt, sz = prep(C, P)
s = score_llr(A, cnt, J)
best = A[int(s.argmax())]
print(f"{TAG} p={P} j={J}: best score {s.max():.2f} of {len(A):,} partitions")
print(f"  winning partition (class -> block): {best.tolist()}")
print(f"  block sizes in classes: {np.bincount(best, minlength=J).tolist()}")

# best shift per block, and the resulting decrypt
groups, shifts = [], []
for b in range(J):
    idx = np.concatenate([np.arange(i, n, P) for i in range(P) if best[i] == b])
    g = np.bincount(C[idx] % 26, minlength=26).astype(float)
    sh = int((g @ LOGE.T).argmax()); shifts.append(sh); groups.append((idx, g, sh))
    prof = np.sort(g/g.sum())[::-1][:5]
    print(f"  block {b}: {len(idx):3d} letters, best shift {sh:2d}, "
          f"top-5 freqs {np.round(prof,3).tolist()}")
print(f"  English top-5 for comparison:      {np.round(np.sort(ENG)[::-1][:5],3).tolist()}")

pt = np.empty(n, dtype=np.int64)
for idx, _, sh in groups: pt[idx] = (C[idx] - sh) % 26
txt = to_str(pt, KA)
print(f"\n  decrypt IoC {ioc(txt):.5f}  (English 0.0667, random 0.0385, PK8 ciphertext {ioc(CT['pk8']):.5f})")
print(f"  decrypt (KRYPTOS alphabet), first 153 letters:\n    {txt}")
print(f"\n  NOTE: under this hypothesis a columnar may sit underneath, so a true hit need not read")
print(f"  as English until the transposition is undone. The letter profile is the diagnostic.")

# multiplicity
NCELL = 18   # 3 targets x 2 alphabets x 3 (p,j) cells
rank_est = 2  # obs sits just under the max of 30 nulls
p1 = rank_est/31
print(f"\n  MULTIPLICITY: single-cell empirical p ~= {p1:.3f} (rank ~{rank_est} of 31 including obs).")
print(f"  Across the {NCELL} cells run, expected number this extreme = {NCELL*p1:.2f}.")
print(f"  Observing one near-tie is exactly what {NCELL} cells predict; it is not evidence.")
