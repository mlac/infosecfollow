"""Phase 1: Period 9 partition attack (weaker agent execution).

Hypothesis: period 9 balanced partitions with j ∈ {2,3,4} distinct letters.
First run: power test on synthetics to validate solver before real targets.
Second run: all three targets (PK8, PK9, PK10), both alphabets.
"""
import numpy as np, json, time, sys
from lib import KA, AZ, CT, to_idx, to_str
from partition_power import prep
from partition_llr import score_llr
from partition_enum import enum_balanced

# Period 9, j values to test. Constraint: j must divide p.
# p=9 divisible by 1,3,9 only. j=1 is trivial (all one letter).
# j=9 is trivial (one class per group). Only j=3 is informative.
P = 9
J_LIST = [3]  # j must divide 9; only j=3 is non-trivial

rng = np.random.default_rng(5555)  # reproducible seed

print("="*70)
print("PHASE 1: Period 9 partition attack")
print("="*70)

# === STEP 1: Power test on synthetics before touching real data ===
print("\n[1/3] POWER TEST: Can the solver recover a planted period-9 key at n=144?")
print("-" * 70)

for j in J_LIST:
    A = enum_balanced(P, j)
    print(f"\nPeriod 9, j={j}: {len(A):,} partitions")

    # Plant 3 synthetic keys with lopsided usage (not all equal)
    planted = [
        np.array([0,1,0,1,2,0,1,2,0]),  # usage: [3,2,1] unequal
        np.array([0,0,1,2,0,1,2,1,0]),  # usage: [3,2,2] more balanced
        np.array([1,2,0,1,2,0,1,0,2]),  # usage: [2,3,2] more balanced
    ]

    recovered = 0
    for plant_idx, plant_part in enumerate(planted):
        # Create synthetic plaintext, apply planted key
        pt_len = 144
        pt = ''.join(rng.choice(list(KA), pt_len))

        # Create synthetic ciphertext by applying the partition key
        ct_idx = to_idx(pt, KA)

        # Apply partition: map each residue class to a letter
        # The partition tells us: class i maps to letter in group plant_part[i]
        key_letters = ['A', 'B', 'C', 'D', 'E'][:j]  # j distinct letters
        key_letter_idx = np.array([to_idx(c, KA)[0] for c in key_letters], dtype=np.int64)
        C = np.zeros(pt_len, dtype=np.int64)
        for pos in range(pt_len):
            res = pos % P  # residue class
            group = plant_part[res]  # which group does this residue map to?
            C[pos] = (ct_idx[pos] + key_letter_idx[group]) % 26

        # Now run the solver on this synthetic
        cnt, _ = prep(C, P)
        s = score_llr(A, cnt, j)
        obs = float(s.max())
        best_part = A[int(s.argmax())]

        # Check if recovered partition matches planted (up to group relabeling)
        # For simplicity: if best partition's score equals the planted score, call it a hit
        planted_score = score_llr(A, cnt, j)[np.where((A == plant_part).all(axis=1))[0][0]] if len(np.where((A == plant_part).all(axis=1))[0]) > 0 else -np.inf

        is_hit = (obs == float(planted_score)) if not np.isinf(planted_score) else False
        recovered += int(is_hit)
        print(f"  synthetic {plant_idx+1}: obs={obs:.1f}, planted_score={planted_score:.1f}, "
              f"recovered={is_hit}")

    power = recovered / len(planted)
    print(f"  → Power: {recovered}/{len(planted)} ({100*power:.0f}%)")

    if power < 0.5:
        print(f"  WARNING: Power < 50% for j={j}. Solver may not be reliable.")

print("\n" + "="*70)
print("[2/3] REAL TARGETS: All three puzzles, both alphabets")
print("="*70)

TARGETS = ['pk9', 'pk8', 'pk10']
NNULL = 30  # matched null size per cell

out = []
t0 = time.time()
tot_scorings = 0

for tag in TARGETS:
    ct = CT[tag]
    n = len(ct)
    print(f"\n{tag.upper()} ({n} letters)")

    # Generate shuffled nulls once per target
    shuf = [''.join(rng.permutation(list(ct))) for _ in range(NNULL)]

    for an, al in (('KA', KA), ('AZ', AZ)):
        C = to_idx(ct, al).astype(np.int64)
        CS = [to_idx(s, al).astype(np.int64) for s in shuf]

        for j in J_LIST:
            A = enum_balanced(P, j)

            # Real data
            cnt, _ = prep(C, P)
            s = score_llr(A, cnt, j)
            obs = float(s.max())
            best_part = A[int(s.argmax())]
            tot_scorings += len(A)

            # Matched nulls
            nulls = []
            for Cx in CS:
                cx, _ = prep(Cx, P)
                nulls.append(float(score_llr(A, cx, j).max()))
                tot_scorings += len(A)

            nm = float(np.mean(nulls))
            nsd = float(np.std(nulls))
            nmx = float(np.max(nulls))
            z = (obs - nm) / nsd if nsd > 0 else 0.0
            above = obs > nmx

            out.append({
                'target': tag, 'alphabet': an, 'p': P, 'j': j,
                'n': n, 'obs': round(obs, 2),
                'null_mean': round(nm, 2), 'null_sd': round(nsd, 2),
                'null_max': round(nmx, 2), 'z': round(z, 2),
                'above': above, 'partition': best_part.tolist()
            })

            status = "*** ABOVE CEILING ***" if above else ""
            print(f"  {an} j={j}: obs={obs:7.1f} null={nm:7.1f}±{nsd:5.1f} max={nmx:7.1f} z={z:+6.2f} {status}")

wall = time.time() - t0
print("\n" + "="*70)
print(f"SUMMARY: {len(out)} cells, {tot_scorings:,} partition scorings, {wall:.0f}s")
print("="*70)

above_cells = [c for c in out if c['above']]
print(f"Cells above matched null max: {len(above_cells)}/{len(out)}")

if above_cells:
    print("\nAbove-ceiling cells (require autopsy):")
    for c in sorted(above_cells, key=lambda x: -x['z'])[:10]:
        print(f"  {c['target']} {c['alphabet']} j={c['j']}: z={c['z']:+.2f} "
              f"(obs={c['obs']:.1f} vs max={c['null_max']:.1f})")
else:
    print("No cells above ceiling. Period 9 is NEGATIVE.")

# Save results
json.dump({
    'phase': 1, 'period': P, 'j_list': J_LIST,
    'cells': out, 'n_scorings': tot_scorings, 'nnull': NNULL,
    'wall': round(wall, 1)
}, open('results/phase1_period9.json', 'w'), indent=1)

print(f"\nResults saved to results/phase1_period9.json")
