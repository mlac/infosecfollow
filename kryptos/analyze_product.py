"""Multiple-testing analysis. The per-cell z is meaningless on its own: 2,040 cells were run.
The honest ceiling is the max over ALL cells of the null, using the 5 matched shuffles per cell
as 5 independent replays of the entire sweep."""
import json, sys, numpy as np
for tag in sys.argv[1:]:
    try: d = json.load(open(f'results/product2_{tag}.json'))
    except FileNotFoundError: print(f"{tag}: not finished"); continue
    C = d['cells']; obs = np.array([c['best_z'] for c in C])
    # each cell carries null_mean and null_max over its 5 shuffles; null_max per cell is the
    # max-z of one full word list, so max over cells of those = a sweep-wide ceiling.
    nmax = np.array([c['null_max'] for c in C]); nmean = np.array([c['null_mean'] for c in C])
    print(f"\n=== {tag}: n={d['n']}, {len(C)} cells, {d['n_word_evals']:,} word-evals, {d['wall_sec']}s ===")
    print(f"  observed best-z over all cells : {obs.max():.2f}  (cell "
          f"{max(C,key=lambda c:c['best_z'])['TA']}/{max(C,key=lambda c:c['best_z'])['KA']}/"
          f"{max(C,key=lambda c:c['best_z'])['mode']} a={max(C,key=lambda c:c['best_z'])['a']} "
          f"b={max(C,key=lambda c:c['best_z'])['b']} dir={max(C,key=lambda c:c['best_z'])['dir']})")
    print(f"  matched-null ceiling (max over cells of the per-cell null max) : {nmax.max():.2f}")
    print(f"  matched-null mean per cell : {nmean.mean():.2f}   observed mean per cell : {obs.mean():.2f}")
    print(f"  cells where observed exceeds its OWN null max : {(obs>nmax).sum()} / {len(C)}  "
          f"(expected by chance with 5 nulls/cell: ~{len(C)/6:.0f})")
    print(f"  VERDICT: observed max {obs.max():.2f} vs ceiling {nmax.max():.2f} -> "
          f"{'ABOVE CEILING - AUTOPSY' if obs.max()>nmax.max() else 'BELOW CEILING - nothing here'}")
    # the discriminating check: on the real controls the true key's NEAR-MISSES cluster at the top.
    top = max(C, key=lambda c: c['best_z'])
    print(f"  top cell's ranked words: {[t[0] for t in top['top'][:8]]}")
    print(f"  (control signature for a real hit, from PK3: PENTIMENTO SENTIMENTO TESTAMENTO "
          f"SENTIMENTS PORTAMENTO -- orthographic neighbours of the true key cluster at the top)")
