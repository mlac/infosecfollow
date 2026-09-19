# Investigation Status: G11 Complete, Next Steps Defined

**Date**: September 3, 2026 | **Latest commit**: `10e5700` (neighbor pass, pk8 AZ m=8 L=6 lag1)

---

## Current State: All Major Families Exhausted

The campaign has now completed comprehensive sweeps across:
- **G8**: Periodic polyalphabetic (periods 2–24, balanced and unbalanced), partition attacks
- **G9**: Six-family workflow; three independent lines converge on PK9's short-period hypothesis
- **G10**: Unbalanced partition enumeration (64.5M configurations on PK9)
- **G11**: Small-modulus sweep (408 cells, 1.77B configurations); neighbor pass on sole survivor

**Verdict for each puzzle:**

| Puzzle | Finding | Tier | Status |
|---|---|---|---|
| **PK9** | Not period 18 (balanced or unbalanced); not periods 2–8, 10; not periods 25–72 | 2 | Open: ~8 periods remain |
| **PK8** | Period 18 (balanced or unbalanced) ruled out in both alphabets | 2 | Open: same scope as PK9 |
| **PK10** | Period 18 ruled out; period-3 partition ruled out; small-modulus sweep clean | 2 | Open: same scope as PK9 |

---

## Explicitly Constrained Search Space (Remaining)

From **§G9 frontier**: periods **≈9 and 11–17**, plus **period 18 with j ≥ 4** (unequal letter usage).

This is the tightest constraint the campaign has achieved. It covers roughly 8 period values rather than the original open family.

### Why this scope remains:

1. **Periods 2–8, 10** — Excluded at power 0.88–1.00 by transposition-invariant period scan (§A2/§A3)
2. **Periods 25–72** — Excluded by wrong-direction IoC argument (§F15)
3. **Period 18 (balanced, j=3)** — Excluded by partition attack with 85% exact recovery (§G8/§G10)
4. **Period 18 (balanced, j≥4 or unequal usage)** — Excluded by unbalanced partition enumeration with power test (§G10)
5. **Period 9** — Not yet run; expected to have decent power at n=144
6. **Periods 11–17** — Not yet run; power will be lower than period 9
7. **Period 18 (j≥5)** — Untested; may need its own j-scaling study

---

## Recommended Next Attack Sequence

### Phase 1: Period 9 via partition attack (immediate payoff if real)

Run the **balanced partition attack** (the solver from §G8) on period 9:
- Fewer classes (9 vs. 18) means ~5× fewer configurations
- Attack expects ~80% exact recovery at n=144 if the key is real
- Run on all three targets (PK8, PK9, PK10), both alphabets
- Include power test (synthetic period-9 keys, lopsided usage patterns)
- **Script**: `partition_attack.py` (already exists with controls)

**Expected cost**: ~30 minutes total across three targets, 2 alphabets.

### Phase 2: Periods 11–17 via period scan sweep

If Phase 1 is negative, run **period scan** on the open periods:
- Transposition-invariant (sufficient for period-18 result to hold)
- Power curves already computed for similar lengths (§A3)
- **Script**: `period_scan.py` (vectorized, uses numpy)
- Run on all three targets; record all p-values and null maxima

**Expected cost**: ~15 minutes.

### Phase 3: Period 18 with j≥5 (if time permits)

If both phases above are negative, run **partition attack at period 18 with j-scaling**:
- Unlike j=3 (three classes), j≥5 means many more partitions
- Will need its own ceiling study (the j=3 ceiling does not apply)
- **Script**: `partition_attack.py` with `j_list=[5, 6, 7, 8]`

**Expected cost**: ~60 minutes per value of j.

---

## Test Discipline (Do Not Deviate)

1. **Match nulls to searches**: Every result needs a proper shuffle/synthetic null
2. **Autopsy at or above ceiling**: Print decrypt, letter frequencies, z-values
3. **Power curves first**: Validate solver recovery before trusting silence on real data
4. **Report all figures**: Real configuration counts, wall-clock time, null maxima, z-values
5. **Grade verdicts**: Tier 1 (impossibility), Tier 2 (exhaustion within rules), Tier 3 (screen only)

---

## Files and Assets Ready to Use

| File | Purpose |
|---|---|
| `partition_attack.py` | Balanced partition solver (period p, j classes); controls for synthetic period-p at n=504 |
| `period_scan.py` | Transposition-invariant period exclusion with power curves |
| `lib.py` | Ciphertexts, solved plaintexts, scoring functions (quadgram, IoC), KRYPTOS alphabet |
| `controls.py` | All seven puzzles round-trip exactly; run if lib.py is touched |
| `quadgrams.npy` | Log10 quadgram model (A–Z order); English −4.25, random −8.23 |
| `OVERNIGHT_RESULTS.md` | Complete campaign record with all power figures, null statistics, verdicts |

---

## Known Traps (From Prior Sessions)

1. **Undersized nulls**: G11's "87 above ceiling" were an artifact of 4-draw shuffles. Always size the null to the search. See §G11 arithmetic.
2. **Letter-stacking decrypts**: Low letter frequency ≠ English plaintext when a single letter is piled up. G11's decrypt had 0.157 vs 0.127. Check the full profile.
3. **Off-by-one in period tests**: Period p means classes 0, 1, ..., p−1. Verify the scan boundaries.
4. **Wordfreq.top_n_list('en', 200000)**: Returns only 183,151 words. Use `rebuild_dict.py` (289k words) if running dictionary sweeps.

---

## Setter's Clues (For Context)

- PK8: "The algorithm is simple. The key has quite a lot of entropy, but some structure."
- PK9: "Solving PK9 probably would help with solving PK8. But PK9 is harder."
- **Key implication**: Neither is exotic; both may share key-structure properties (hence the period constraint now applies to both).

---

## How to Resume

```bash
cd kryptos
OMP_NUM_THREADS=1 python3 verify.py      # Trust baseline; should complete in ~3 min
python3 partition_attack.py period=9      # Phase 1, if targeting PK9
```

If any control fails, every negative in `OVERNIGHT_RESULTS.md` is void. Run it first.

---

## Success Criteria

- A real key will be recovered at rank ≤ 5 of its search space and must round-trip exactly
- Supporting evidence: power curve ≥ 80% recovery on synthetic, matched null placing observed well below ceiling
- Anything below the ceiling but lingering is a screen result (Tier 3), not a verdict

---

**Next Session Start**: Focus **Phase 1** (period 9, partition attack) on PK9 first, then replicate to PK8 and PK10. Phase 1's power is highest and expected payoff is clearest.
