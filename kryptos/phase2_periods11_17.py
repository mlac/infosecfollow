"""Phase 2: Periods 11-17 transposition-invariant period scan.

These periods were not excluded by G8/G9 analyses. We now run the period scan,
which is transposition-invariant, on all three targets and both alphabets.

Power already computed in §A3; we have power curves for these lengths.
"""
import numpy as np, json, time, sys
from lib import KA, AZ, CT, to_idx, ioc, to_str

print("="*70)
print("PHASE 2: Periods 11-17 transposition-invariant scan")
print("="*70)

TARGETS = ['pk9', 'pk8', 'pk10']
PERIODS = list(range(11, 18))  # 11, 12, 13, 14, 15, 16, 17
NNULL = 100  # matched null: shuffle-based
rng = np.random.default_rng(6666)

out = []
t0 = time.time()

for tag in TARGETS:
    ct = CT[tag]
    n = len(ct)
    print(f"\n{tag.upper()} ({n} letters)")

    # Generate shuffled nulls once per target
    shuf = [''.join(rng.permutation(list(ct))) for _ in range(NNULL)]

    for an, al in (('KA', KA), ('AZ', AZ)):
        C = to_idx(ct, al).astype(np.int64)
        CS = [to_idx(s, al).astype(np.int64) for s in shuf]

        for p in PERIODS:
            # Compute IoC for each residue class; use minimum (most random-like)
            # or mean (average alignment).
            # Transposition-invariant: pool residue classes and look at chi-sq of
            # letter distribution across classes.

            # Method: class-census invariant (chi-sq on letter distribution by class)
            chi2_obs = 0.0
            for letter_idx in range(26):
                # Count how many times this letter appears in each class
                class_counts = np.zeros(p, dtype=int)
                for pos, c in enumerate(C):
                    if c == letter_idx:
                        class_counts[pos % p] += 1
                # Chi-sq: compare observed to uniform
                expected = len([1 for c in C if c == letter_idx]) / p
                for count in class_counts:
                    diff = count - expected
                    chi2_obs += (diff * diff) / (expected + 1e-10)

            # Null: same chi-sq on shuffled ciphertexts
            chi2_nulls = []
            for Cx in CS:
                chi2_null = 0.0
                for letter_idx in range(26):
                    class_counts = np.zeros(p, dtype=int)
                    for pos, c in enumerate(Cx):
                        if c == letter_idx:
                            class_counts[pos % p] += 1
                    expected = len([1 for c in Cx if c == letter_idx]) / p
                    for count in class_counts:
                        diff = count - expected
                        chi2_null += (diff * diff) / (expected + 1e-10)
                chi2_nulls.append(chi2_null)

            nm = np.mean(chi2_nulls)
            nsd = np.std(chi2_nulls)
            nmx = np.max(chi2_nulls)
            z = (chi2_obs - nm) / nsd if nsd > 0 else 0.0
            above = chi2_obs > nmx

            out.append({
                'target': tag, 'alphabet': an, 'period': p,
                'n': n, 'obs': round(chi2_obs, 1),
                'null_mean': round(nm, 1), 'null_sd': round(nsd, 1),
                'null_max': round(nmx, 1), 'z': round(z, 2),
                'above': above, 'nnull': NNULL
            })

            status = "*** ABOVE CEILING ***" if above else ""
            print(f"  {an} p={p:2d}: obs={chi2_obs:8.1f} null={nm:8.1f}±{nsd:6.1f} max={nmx:8.1f} z={z:+6.2f} {status}")

wall = time.time() - t0
print("\n" + "="*70)
print(f"SUMMARY: {len(out)} cells (7 periods × 3 targets × 2 alphabets), {wall:.0f}s")
print("="*70)

above_cells = [c for c in out if c['above']]
print(f"Cells above matched null max: {len(above_cells)}/{len(out)}")

if above_cells:
    print("\nAbove-ceiling cells (require autopsy):")
    for c in sorted(above_cells, key=lambda x: -x['z'])[:10]:
        print(f"  {c['target']} {c['alphabet']} p={c['period']}: z={c['z']:+.2f} "
              f"(obs={c['obs']:.1f} vs max={c['null_max']:.1f})")
else:
    print("No cells above ceiling. Periods 11-17 are NEGATIVE.")

# Save results
json.dump({
    'phase': 2, 'periods': PERIODS,
    'cells': out, 'nnull': NNULL,
    'wall': round(wall, 1)
}, open('results/phase2_periods11_17.json', 'w'), indent=1)

print(f"\nResults saved to results/phase2_periods11_17.json")
