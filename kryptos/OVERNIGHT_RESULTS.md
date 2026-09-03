# OVERNIGHT RUN — PK8 / PK9 / PK10 — RESULTS

**Status: no puzzle solved.** That is the likeliest outcome and it is what happened. What follows
is a set of eliminations, several of them substantially stronger than anything in the prior
elimination map, plus a rebuilt frontier. Read §A first — it changes what is worth running next.

Run date 2026-09-03. Working dir `kryptos/`. Harness: all seven solved puzzles round-trip exactly
(`python3 controls.py`).

---

## A. HEADLINE FINDINGS

### A0. THE MOST IMPORTANT RESULT OF THE NIGHT — most short-message negatives, mine and the prior campaign's, are underpowered

Doctrine says validate a solver before trusting its silence. Applied at the *cell* level that is
easy, and both this campaign and the prior one passed it: the two-word product solver recovers the
true key of a 153-letter synthetic at rank 1 of 35,831. But a sweep does not report one cell — it
reports the **maximum over 2,040 cells**, and that maximum has its own noise floor. The right
control is therefore: run the *entire grid* on a synthetic of the same length that really does have
the key you are searching for, and ask whether it beats the ceiling the real sweep produced.

That was done tonight, and the answer changes the verdicts:

| synthetic | true key's best cell | sweep-wide max on the synthetic | real-sweep ceiling | detected? |
|---|---|---|---|---|
| n=153, OCHRE × VERDIGRIS, columnar underneath | z = 5.92 / 5.98 | 7.17 (a **noise** cell, KA/AZ/sub 9,10) | 7.87 | **NO** |
| n=144, ANVIL × QUENCHING, columnar underneath | z = 4.33 / 5.97 | 7.16 (a **noise** cell) | 7.83 | **NO** |
| n=504, OCHRE × VERDIGRIS, columnar underneath | z = 10.44 / **15.57** | **15.57 — the TRUE cell (KA/KA/sub, a=5, b=9), top word VERDIGRIS** | 6.75 | **YES, overwhelmingly** |

At 144–153 letters a *genuine* two-word product key produces z ≈ 6, while the noise maximum over
2,040 correlated cells sits at 7.8–7.9. The signal is below the noise floor of the search that is
looking for it. **No amount of re-running helps.** At 504 letters the same key produces z = 15.57
against a 6.75 ceiling and the true cell wins the whole grid outright — a factor of 3.5 in message
length is the difference between a search that cannot see its target and one that cannot miss it.

The same holds for the blind Hill sweep: run on synthetic Hill ciphertexts it fires above its own
ceiling **6/6 at n=279 and 6/6 at n=504, but only 3/6 at n=153 and 2/6 at n=144**.

**Consequences, applied honestly to my own results:**

* PK8 and PK9 two-word product keys: **Tier 3, not Tier 2.** Those specific keys are not indicated,
  but the family is not exhausted. §6's existing Tier 2 entry for the same family rests on a
  cell-level control and should be downgraded for the same reason.
* PK8 and PK9 blind Hill: **Tier 3.**
* PK8 and PK9 progressive keys: **partial**. Synthetic progressive keys at n=144 scored z = +3.7 to
  +8.7 depending on the progression law, while the PK9 sweep's ceiling was +4.32 — so the stronger
  progressions would have been caught and the weakest (block p=9, d=3) would not.
* **PK10 keeps its Tier 2 verdicts.** 504 letters is 3.5× the signal, and every PK10 sweep that was
  power-checked fired on its synthetic.

**What stays fully powered at 144–153 letters** — and is therefore where short-message effort
belongs: tests whose false-positive rate is set by *exact algebra* rather than by ranking a large
candidate list. The crib × key-structure consistency test has a per-structure false-positive rate
of 2.7 × 10⁻¹⁶ and detects a true crib with probability 1 regardless of message length; likewise
the wrap-crib join and the multiset test. Those negatives hold at full strength. Ranking searches
over ~30,000 candidates do not, and at these lengths they never will.

This also reframes the setter's "PK9 is harder": whatever the algorithm, 144 letters is below the
threshold at which dictionary-scale search works at all. **PK10 is the only one of the three where
brute-force search has real power, and it should be the entry point.**


### A1. PK10 has no periodic key of period 2–100. Tier 2, transposition-invariant.

Statistic: mean IoC of the residue classes mod *p*. This is invariant to a columnar transposition
sitting under the substitution (the architecture of PK4 and PK6), and it is alphabet-agnostic — it
does not care whether the tableau is KRYPTOS-keyed, nor what the key letters are, only that the key
is *constant within a column*.

Null: the identical statistic on 500 letter-shuffled copies of PK10 itself.
Power: the identical statistic on synthetic period-*p* ciphertexts built from real sibling-plaintext
English pushed through a width-8 columnar and then a random period-*p* key.

| p | observed z | z a TRUE period-p cipher would give | power at z>3 |
|---|---|---|---|
| 2 | +0.32 | +64.19 ± 2.58 | 1.00 |
| 5 | +0.64 | +29.83 ± 1.68 | 1.00 |
| 9 | (see results/period_pk10.json) | — | 1.00 |
| 45 (PK4's own lcm) | **−0.01** | **+7.49 ± 1.17** | 1.00 |
| 63 | +1.48 | +3.84 ± 1.12 | 0.73 |
| 72 | −0.56 | +7.00 ± 1.28 | 1.00 |

The scan ran to **period 100** (the limit where each residue class still holds ≥5 letters). Every
period from 2 to 100 except 63 is excluded at power ≥0.8 with the observed z inside ±2, and the
**maximum observed z across all 99 periods is +1.92** (at p=47). Even at p=63, where power dips to
0.71, a true cipher would give z=+3.84 against an observed +1.47.
**Consequence: every two-word product key whose lcm is ≤ 72 is dead for PK10** — a product key
`k1[i%a] + k2[i%b]` *is* a periodic key of period lcm(a,b). PK4's own (5,9)→45 construction is
therefore ruled out for PK10, as is PK3's (10,8)→40, PK1's 10, and PK6's 6.
Caveat, stated plainly: this holds for the *transposition-innermost* architecture (transpose then
substitute), which is what both solved two-layer puzzles do. A substitute-then-transpose
architecture would defeat the column test, though not the ciphertext-IoC argument in A2.

### A2. Effective key period from ciphertext IoC alone (transposition-invariant)

Each hypothesis simulated 400× at the exact message length, plaintext drawn from the real sibling
plaintexts. Consistent = |z| < 2.

| target | observed IoC | excluded | consistent with |
|---|---|---|---|
| PK8 (153) | 0.0395 | plaintext (z −8.2), period 2–3 | running key (z −0.22), random/long key (+0.57), period ≥ 4 |
| PK9 (144) | **0.0445** | random one-time key (z **+3.27**) | **running key (+1.84)**, period 2–18 |
| PK10 (504) | 0.0388 | plaintext (−21.3), **periods 2–8** (z −2.3 to −3.6) | running key (−1.73), random/long key (+0.58), period ≥ 9 |

PK9 is the only one of the three whose ciphertext is *not* consistent with a random long key. Its
census χ² against uniform is 47 on 25 df (p≈0.005); PK8 and PK10 are both 29 and flat. Combining
A1, A2 and the prior Tier-2 kill of periods 2–24: for PK9 the short-period explanations are
excluded by the power table below, which leaves **running key as the surviving explanation of PK9's
anomaly** — and the setter's "PK9 is harder" is exactly what a running key would mean.

### A3. Period exclusions for PK8 and PK9, with power (this is the part §6 was missing)

§6's period sweep was *quadgram-optimized*, which is not transposition-invariant, and its
transposition-invariant companion (sorted-profile) only reached period 12. The table below is
transposition-invariant at every period and reports power, so a silence means something.

PK9 (n=144): periods **2, 3, 4, 5, 6, 8** excluded at power 0.88–1.00. Power falls under 0.8 from
p=9 and collapses to 0.06 at p=18 — the test is simply blind at longer periods on 144 letters.
PK8 (n=153): periods **2–6, 8–13, 15–17** excluded at power 0.85–1.00.

**The one thing that did not lie down: p=7.** PK8 observed z=+3.25 and PK9 observed z=+2.41, both
at p=7, and both again elevated at p=14. Autopsy in §C1. Verdict: not a hit — a true period-7 PK8
would give z=+6.95±1.69, so the observed +3.25 is 2.2σ *below* the true-cipher distribution, and
across 3 targets × ~30 periods = ~90 correlated tests a max of +3.25 is close to expectation.
But it is the only place two targets agree, and it is worth one dedicated pass.

### A4. The two-word product solver is validated on real puzzles, not just synthetics

`product2.py` decomposes the search: peel the correct length-*a* key and every residue class mod
*b* becomes monoalphabetic, so the two words can be found *independently* — N_a + N_b candidates
instead of N_a × N_b. It survives an unknown columnar underneath.

| control | true key | rank | z |
|---|---|---|---|
| **real PK3 ciphertext** (280 ltr) | PENTIMENTO | **1 / 21,570** | +9.5 |
| **real PK3 ciphertext** | ORDINATE | **1 / 38,356** | +5.2 |
| **real PK4 ciphertext** (224 ltr, columnar underneath) | OCHRE | **1 / 38,208** | +7.8 |
| **real PK4 ciphertext** | VERDIGRIS | **1 / 29,973** | +9.3 |

Note PK3's key `q3enc(PENTIMENTO×4, ORDINATE)` *is* a two-word product, because lcm(10,8)=40
equals the key length. Verified: `q3enc(PT3, ['PENTIMENTO','ORDINATE']) == CT['pk3']`.

### A5. Dictionary correction that invalidates part of the prior campaign

`wordfreq.top_n_list('en', 200000)` yields 183,150 words and **does not contain PENTIMENTO or
WHITESMITH** — i.e. a 183k-word sweep could not have found PK3's own key. The full list
(`top_n_list('en', 500000)` → 289,026 words) contains every known key. All sweeps here use the
289k list. Any prior sweep run on a ~180k list should be treated as re-runnable, not settled.

---

### A6. PK10 is not a running key. Tier 2.

A running key (English text over English text) leaves a ciphertext census equal to the
**convolution** of two English unigram distributions, which is distinctly non-uniform (min 0.0226,
max 0.0509 against uniform 0.03846). A long or random key leaves a flat census. The
log-likelihood ratio between those two hypotheses, simulated 4,000× at the exact message length:

| target | LLR (KA) | vs RUNNING-KEY sim | vs LONG/RANDOM-KEY sim | favours |
|---|---|---|---|---|
| PK8 (153) | −4.95 | z = **−3.26** | z = −0.48 | long/random key |
| PK9 (144) | −1.63 | z = −1.99 | z = +0.65 | long/random key |
| PK10 (504) | −13.03 | z = **−5.16** (AZ: −6.30) | z = −0.17 (AZ: −1.16) | long/random key |

PK10 is 5–6 σ from the running-key hypothesis and sits exactly on the flat-keystream hypothesis.
Combined with A1: PK10's keystream is **aperiodic over 504 letters and near-uniform in its marginal
distribution** — it behaves like a long generated key, not like a text. The same argument excludes
*plaintext autokey* for PK10, since there the keystream is also English text.

**Scope, checked and narrowed.** The result holds when the key text is read in the same tableau as
the plaintext — which is exactly what PK5 does (running key = PK4's plaintext, same alphabet). It
does **not** hold if the key text is read through an independent keyed alphabet: averaging the
convolution over 400 random alphabet permutations flattens it, and the two hypotheses then separate
by only z = −1.01 on PK10 rather than −5.16. That case remains open, and is worth stating because
the first version of this analysis overclaimed it.

### A7. Substitute-then-transpose is excluded for PK10. Tier 2.

Every result above assumes transposition-innermost (what PK4 and PK6 do). The other order was
tested separately: if `ct = col_enc(substituted, perm)` at width W with n divisible by W, then
ciphertext block j is `sub[perm[j]::W]`, whose block boundaries depend only on W and n — not on the
unknown permutation — and whose in-block key period is q = P/gcd(W,P). Scanning (W, q) therefore
detects the substitution without knowing perm.

* **PK10: 116 of 116 (W,q) cells at power 1.00, max observed z = +2.83.** Excluded.
* PK8: max observed z = +2.06 over 14 cells. PK9: max +3.87 at (W=3, q=1) — autopsied in §C2 and
  discharged; a true cipher of that shape gives z = +8.99 ± 1.76, so the observation is 2.9 σ
  *below* the true-cipher distribution and below a 3,000-shuffle ceiling.

### A8. The crib attack (the requested last shot): 54 million tests, zero passes — and fully powered at every length

The productive form of a crib here is not "does the decrypt read as English" — it is that a crib
pins the keystream **exactly**, and a structured key must then satisfy hard linear constraints.
For a key `k[i] = Σ_f u_f[i mod p_f]`, consistency of the derived keystream is equivalent to
`R·K ≡ 0 (mod 26)` where R is the left null space of the incidence matrix. Z26 = GF(2) × GF(13) by
CRT and both are fields, so R was computed over each. A 24-letter crib against a (5,9) product
gives 11 GF(2) plus 11 GF(13) checks — a false-positive rate of **2.7 × 10⁻¹⁶**. No dictionary is
involved: this tests the *structure* of the key, not its vocabulary, which is exactly what the
setter's "quite a lot of entropy, but some structure" describes.

Controls: on the real PK3 the only passing two-factor structure is **(8,10)** — its true one. On
the real PK1 the test returns period **10** exactly. Matched null: 42,200 tests on random cribs
gave **0** false passes.

Corpus: **10,685 cribs**, 18–29 letters, built in the diary's own register — elapsed-time openings
(the form four of the seven solved plaintexts use: SEVENTHMONTH / TWOYEARSIN / FOURTEENDAYSIN /
THREEWEEKSIN), `INVESTIGATIONLOGITEM` + numeral (PK1's own opening, and the user's suggestion),
numbers *not* yet used in the series, and 28 literal continuations of PK7's closing.

**Executed: 54,208,692 effective tests** — 10,685 cribs × 404 key structures (single periods 2–24,
all two-factor pairs 3–16, all three-factor triples 3–14, all four-factor quadruples 3–10) × 3
targets × 2 alphabets × 3 modes × {prefix, suffix}. Underpowered structure/length combinations
(false-positive rate > 10⁻⁶) were skipped and counted: 103,644.
**Expected false positives under the null: 0.67. Observed passes: 0.** (Of those 54.2M tests, ≈36.1M
are distinct — the `add` mode is redundant with `sub` here, see §F7 — which lowers the expected
false-positive count to ≈0.45 and changes nothing else.)

Unlike the ranking sweeps, **this test does not lose power on a short message** (§A0): its
false-positive rate is set by exact algebra, so a correct crib passes with probability 1 whether the
message is 144 letters or 504. Its only failure mode is the crib not being in the corpus. That is
why the corpus was later enlarged to 48,616 (§F8).

Scope: the crib sits at fixed ciphertext positions, so this assumes **no transposition**. That is
the honest limit — see §E for the width-9 extension that was designed but not run.

---

## B. WHAT RAN, WITH REAL COUNTS AND WALL-CLOCK

| sweep | configurations actually executed | wall | observed best | matched-null ceiling | verdict |
|---|---|---|---|---|---|
| **Gromark, digit primers** | **1.235 × 10¹⁰ trial decryptions** (all 10⁷ primers at L=7, all 10⁸ at L=8) | 5,700 s | IoC .0637 | .0628 pooled | **Tier 2** (§F12) |
| PK10 two-word product, full grid | 2,040 cells / 245,423,952 word-evaluations | 1,728 s | z = 6.40 | 6.75 | **Tier 2 dead** |
| PK8 two-word product, full grid | 2,040 cells / 245,423,952 word-evaluations | 542 s | z = 7.07 | 7.87 | Tier **3** — underpowered, §A0 |
| PK9 two-word product, full grid | 2,040 cells / 245,423,952 word-evaluations | 521 s | z = 7.15 | 7.83 | Tier **3** — underpowered, §A0 |
| PK8 three-word product grid | 2,796 cells / **329,959,512 word-evals** | 1,716 s | z = 7.07 | 8.03 | Tier 3, §A0 (§F10) |
| PK9 three-word product grid | 2,688 cells / **317,784,240 word-evals** | 1,617 s | z = 7.24 | 7.29 | Tier 3, §A0 (§F10) |
| PK10 three-word product grid | ~5,500 cells | running | §F10 | — | — |
| PK10 period scan 2–100 | 99 periods × (500 nulls + 120 power sims) | 320 s | z = **+1.92** | ±2, power 1.00 | **Tier 2 dead** |
| PK8 period scan 2–30 | 29 periods × 620 | 90 s | z = +3.25 (p=7) | §C1 | dead p 2–6, 8–13, 15–17 |
| PK9 period scan 2–28 | 27 periods × 620 | 85 s | z = +2.41 (p=7) | §C1 | dead p ≤ 8, p=10 |
| Mutual-IoC periodic solver, p 2–24 | 3 targets × 2 alphabets × 23 periods × 400 nulls × 30 restarts | 400 s | §C1 | per-period | supplementary to the period scan; no sweep-level power test, so **Tier 3** on its own |
| Blind Hill, k = 2, 3, 4, offsets P 1–6 | PK7 control + 3 targets, **9,039,240 row-evaluations** | 900 s | 0 above ceiling | per-cell | **Tier 2 (PK10)**, Tier 3 PK8/PK9 (§F2) |
| Substitute-then-transpose scan | pk10 116 (W,q) cells at power 1.00, pk8 14, pk9 43 | 200 s | z = +3.87 (pk9) | §C2 | **Tier 2 dead (PK10)** |
| Progressive-key scan | pk10 15,600 cells, pk8 4,680, pk9 4,368; 150 nulls each | 300 s | z = +4.70 (pk10) | ≈ +4.4 expected | Tier 3, at expectation |
| Running-key census LLR | 3 targets × 2 alphabets × 8,000 sims | 30 s | z = −5.16 (pk10) | — | **Tier 2 (PK10)**, same-tableau only (§A6) |
| **Crib × key-structure, original corpus** | **54,208,692 tests** (≈36.1M distinct) | 200 s | 0 passes | 0.67 expected FP | **Tier 2** (no transposition) |
| **Crib × key-structure, enriched corpus** | **355,980,204 tests** (48,616 cribs) | 620 s | 0 passes | 3.20 expected FP | **Tier 2** (no transposition) |
| **Crib sweep on 48 coupling texts** | **367,133,184 tests** | 480 s | 0 passes | 4.12 expected FP | **Tier 2** (§F5) |
| Crib at every offset | 16,525,920 tests, 47 recurring phrases | 15 s | 0 passes | 0.19 expected FP | **Tier 2**, and bounded on principle (§F11) |
| Wrap-crib conjunction | 3,214,350 hash-join tests | 30 s | 0 agreements | 0.01 expected FP | **Tier 2** (§D) |
| Multiset crib (width W, key period \| L) | 1,000,200 tests | 300 s | 0 passes | 0 of 32,000 null cribs | **Tier 2** within its shape (§F1) |
| Derived coupling texts, period + product | 48 texts × ~30 periods + product grids | running | +3.76 / +2.62 | §F5 | Tier 3 |
| Shared-keystream coupling | 24 combos × every offset + 60 nulls per scan | 40 s | all below | — | Tier 3 — **weak test** (§C4) |

**Crib-family total: ~797 million exact tests, zero passes.**

Product-grid cell definition: target × {KA, A-Z} text alphabet × {KA, A-Z} key alphabet ×
{subtract, add, beaufort} × 91 length pairs (3 ≤ a < b ≤ 16) × up to 2 decomposition directions,
5 letter-shuffle nulls per cell. Word list 289,026 words, lengths 3–16.

### B1. The shape of the product results (read with §A0: this is decisive for PK10, indicative only for PK8/PK9)

* **PK8**: max z 7.07, ceiling 7.87. Cells beating their own null: **361 / 2,040** vs ~340 expected.
* **PK9**: max z 7.15, ceiling 7.83. Cells beating own null: **302 / 2,040** — *below* chance.
* **PK10**: max z 6.40, ceiling 6.75. Cells beating own null: 386 / 2,040.

All three sweeps sit exactly on their nulls, and the top-ranked words are orthographically unrelated
(PK8: HENNELL, HANGEUL, HANNELE, DOUBLES; PK9: BREWMASTERS, GANGMASTERS, BANDMASTERS;
PK10: DIMMADOME, CAPITATED, OBERKAMPF, LUMINARIA). A genuine hit looks different — on the real
PK3 the top five were PENTIMENTO, SENTIMENTO, TESTAMENTO, SENTIMENTS, PORTAMENTO: the true key
with its orthographic neighbours stacked underneath, because a near-miss still cancels most of
the keystream. That clustering is the signature to look for, and it is absent everywhere here.

---

## C. AUTOPSIES — everything that reached or passed a ceiling

Four things crossed a ceiling at some point tonight. All four died. Each is written up because the
*pattern* of how they died is reusable.

### C1. PK8, period 7, mutual-IoC solver — killed by enlarging the null

A new transposition-invariant solver was built for this run: align the p column histograms by
shift to maximise pooled IoC. It needs no plaintext alphabet, no quadgram model, and it survives an
inner columnar — none of which is true of §6's quadgram-optimised period sweep.

* With **25** shuffle-nulls: observed 0.0618, null max 0.0572 → *above ceiling*.
* With **200**: observed 0.0618, null max 0.0574 → still above, z = +4.80.
* With **2,000**: null max = **0.06183** — *exactly the observed value*. Empirical p = 0.0005.

The lesson is the doctrine's: an undersized null manufactures hits. The statistic maximises over
26⁶ shift vectors on 22 letters per column, so it overfits hard and its null has a long tail.

The autopsy also shows *how* it overfits. Sorted letter profile of the aligned residual against
English:

```
observed  0.163  0.078  0.078  0.072  0.065  0.065  0.052  0.046
English   0.138  0.104  0.085  0.076  0.072  0.071  0.069  0.063
```

One spiked letter and then a flat tail — the optimiser stacked the commonest ciphertext letter of
each column onto a single output letter. English decays smoothly. χ² of the sorted profile against
English = 85.6. Independently, the quadgram solve at p=7 reached −6.742 against a null max of
−6.579 (English is −4.25), i.e. below its own ceiling. **PK8 p=7 is dead on both solvers.**
The same treatment discharged PK8 p=14, PK9 p=7 and PK9 p=14.

Across the full mutual-IoC grid (3 targets × 2 alphabets × 23 periods, 400 shuffle-nulls and 30
restarts per cell) the only cells above their own null max were PK8 at p=7 in both alphabets, and
both are explained above. PK9 max z +3.18, PK10 max z +2.19, zero cells above ceiling.

### C2. PK9, substitute-then-transpose at W=3 — killed by the true-cipher comparison

Observed z = +3.80, empirical p = 0.0017 against 3,000 shuffles, but *below* the 3,000-shuffle
ceiling. Decisive check: **a genuine period-3-then-width-3 cipher gives z = +8.99 ± 1.76** at this
length, so the observation sits 2.9 σ *below* the distribution it would have to be drawn from.
Block IoCs are 0.0514 / 0.0638 / 0.0505 where three 48-letter English blocks would be ≈0.065 each.
Over 43 cells for PK9 the family-wise rate is ≈0.29. Dead.

### C3. PK10, two-word product at (a=9, b=14) — killed by multiplicity and by the decrypt

The only cells the period argument in A1 does not already kill are those with lcm > 100. Filtering
the PK10 sweep to those 504 cells, the observed max z 6.40 exceeds that subset's 5-replay ceiling
of 6.01. Rebuilt with **200 replays**: null mean 4.536, sd 0.338, max 5.516, so the single-cell
empirical p < 0.005. But the cell was one of **2,040** in the sweep, which predicts ~10 cells this
extreme by chance, and the full-sweep ceiling (6.75) exceeds it. Cells beating their own null in
the lcm>100 subset: 88 of 504, against 84 expected.

The decrypt settles it. Peeling the top word (DIMMADOME) at period 9 and solving the period-14
residual transposition-invariantly gives pooled IoC 0.0518 (English 0.065) and a quadgram score of
**−7.96** where English is −4.25 and random is −8.23. The plaintext head reads
`BVGRBGTPXNHKBZTHHVCJHOHHWSPGIFCMWPAMALHTSCPHHAJCERKSHHYQHAHIHOTVDHHYDTHYEGAHHHBAJGIHWVDVHW` —
H-stacking, the same overfit signature as C1. The ranked words (DIMMADOME, CAPITATED, OBERKAMPF,
LUMINARIA, CAPITAINE) share no orthography, unlike a real hit. Dead.

### C4. The shared-keystream coupling test is honestly under-powered

No pair of PK8/PK9/PK10 shows a shared keystream at any offset, in either alphabet, forward or
reversed — every scan below its matched ceiling. But the test's separation is only **0.9 σ**: a
genuine shared-key pair gives IoC 0.0402 ± 0.0028 against 0.0384 ± 0.0019 for independent keys at
n=144. So this is a **Tier 3 screen, not an exhaustion**, and it should not be cited as ruling out
a shared key. It is recorded here mainly so the next session does not mistake it for one.

---

## D. UPDATED ELIMINATION MAP (replaces §6 of PK_CONTEXT.md)

Everything from §6 still stands except where noted. New entries from tonight are marked **[NEW]**.
Tier 1 = proven impossible · Tier 2 = exhausted within stated rules · Tier 3 = screen, family open.

### Tier 1 — unchanged
* All 26 letters present in all three → no 24/25-cell cipher can be the final layer.
* Census χ² against English 646 / 1071 / 3941 on 25 df → no pure transposition anywhere.
* Length preserved → no length-changing construction at the outer layer.

### Tier 2 — exhausted (each with a positive control that passes)

Carried over from §6: periodic polyalphabetic p 2–24 (quadgram-scored, four Quagmire pairings);
sorted-profile period test p 2–12; 325 thematic keyed alphabets × p 3–14; single dictionary key;
Hill 2×2 and 3×3 with additive periods 1–3; affine decimation; antipodal coupling; joint width-9
multiple anagramming; joint single-key screen.

**[NEW] PK10 — no periodic keystream of period 2–100, in any alphabet, any mode, with or without an
inner columnar.** 99 periods, 500 shuffle-nulls and 120 power sims each; max observed z **+1.92**;
power 1.00 at every period except 63 (0.71). Control: the statistic is key-value-agnostic, so its
power is unaffected by what the key letters are. *This subsumes the whole two-word product family
at lcm ≤ 100 for PK10, including PK4's own (5,9)→45 and PK3's (10,8)→40.*

**[NEW] PK10 — not substitute-then-transpose.** 116 of 116 (W,q) cells at power 1.00, max z +2.83.

**[NEW] PK10 — not a running key (nor plaintext autokey) whose key text is read in the same
tableau as the plaintext.** Census log-likelihood ratio is 5.2 σ (KA) and 6.3 σ (AZ) from the
running-key hypothesis and 0.2 σ from the flat-keystream hypothesis. *Tier 3, not Tier 2, if the key
text may be read through an independent keyed alphabet* — that variant separates by only 1.0 σ and
stays open (§A6).

**[NEW] PK10 — two-word additive product keys from dictionary words, full grid.** (PK8 and PK9
ran the identical grid but are **Tier 3**, not Tier 2 — see §A0; the search is underpowered at those
lengths.)
2,040 cells and **245,423,952 word-evaluations per target** (736M total): {KA, A-Z} text alphabet ×
{KA, A-Z} key alphabet × {sub, add, beaufort} × 91 length pairs 3–16 × up to 2 decomposition
directions × 5 letter-shuffle nulls. Observed maxima 7.07 / 7.15 / 6.40 against matched ceilings
7.87 / 7.83 / 6.75. Controls: recovers **PENTIMENTO** and **ORDINATE** from the real PK3 ciphertext
and **OCHRE** and **VERDIGRIS** from the real PK4 ciphertext (which has a columnar underneath), all
at rank 1 of 21k–38k, z +5.2 to +9.5. Word list 289,026, lengths 3–16.
*This closes frontier item 1 — all 58 PK10 length pairs, and 91 in fact.*

**[NEW] PK8, PK9 — periods 2–8 (PK9 also 10) and PK8 periods 2–6, 8–13, 15–17**, transposition-
invariantly, at power 0.85–1.00. §6's period result was quadgram-scored and therefore blind to an
inner columnar; this one is not.

**[NEW] Mutual-IoC periodic solver, p 2–24, all three targets, both alphabets**, 400 shuffle-nulls
and 30 restarts per cell. A transposition-invariant, alphabet-agnostic *solver* (not just a
detector) that §6 never had. Nothing survives; the two PK8 p=7 cells that crossed a 400-null
ceiling die against a 2,000-null one (§C1).

**[NEW] Crib × key-structure consistency, no-transposition case.** 54,208,692 effective tests:
10,685 cribs × 404 key structures (single periods 2–24, all two-factor pairs 3–16, all three-factor
triples 3–14, all four-factor quadruples 3–10) × 3 targets × 2 alphabets × 3 modes × {prefix,
suffix}. Expected false positives 0.67, **observed 0**. Controls: recovers PK3's true (8,10) as the
*only* passing structure and PK1's period 10 exactly; 42,200 null tests gave 0 false passes.

**[NEW] Wrap-crib conjunction.** 3,214,350 hash-join tests over wrap periods Q (PK8 124–147 plus
144, PK9 115–138, PK10 144–498), requiring a prefix crib and a suffix crib to agree exactly on the
6–29 overlapping key letters. Zero agreements; expected false positives 0.01. This is the only
test that can see a key *shorter than the message*, which no period scan can reach.

### Tier 3 — screens only, family open

All §6 Tier 3 entries stand. Added tonight:

* **[NEW] Progressive / sliding keys** — k[i] = key[i%p] + (i//p)·d, + i·d, and + (i(i+1)/2)·d, over
  every (p, d) with both alphabets: 15,600 cells on PK10, 4,680 on PK8, 4,368 on PK9, 150 nulls per
  cell. Max z +4.70 on PK10 against ≈+4.4 expected for 15,600 correlated cells. Controls recover
  synthetic progressive keys at rank 1 with z +3.7 to +28.7 at all three lengths. Nothing, but only
  three progression laws were tried.
* **[NEW] Shared keystream between the three targets** — every ordered pair × 2 alphabets × forward
  and reversed × every offset. All below their matched ceilings, **but the test separates the
  hypotheses by only 0.9 σ** (§C4). Weak; do not cite as an exhaustion.
* **[NEW] Derived coupling texts** (frontier item 6): d = c_x ± c_y for every ordered pair, both
  alphabets, forward and reversed — 48 derived texts, each given a transposition-invariant period
  scan with power and a two-word product grid. See §D1 for the state at write-up time.

### D1. Corrections to the prior campaign

* **The dictionary was too small.** `wordfreq.top_n_list('en', 200000)` gives 183,150 words and
  **does not contain PENTIMENTO or WHITESMITH** — a sweep on that list could not have found PK3's
  own key. The full list gives 289,026 and contains every known key. Any prior sweep run at ~180k
  words should be re-run, not trusted.
* **PK3's key is a two-word product.** `q3enc(PT3, ['PENTIMENTO','ORDINATE']) == CT['pk3']`,
  verified, because lcm(10,8)=40 equals the key length. So the product family is the series'
  signature construction, and its exhaustion on PK8/9/10 is more meaningful than it looks.
* **PK9's IoC anomaly is real but should not be over-read.** IoC 0.0445 at n=144 is z=+3.24
  (p=0.0039, ≈0.012 after the three-target multiplicity) and χ² vs uniform is 47 on 25 df. But its
  census log-likelihood favours a *flat* keystream over a running key (z=+0.65 vs −1.99), and the
  short periods that would explain the IoC are excluded at power 0.88–1.00. After the number of
  statistics computed tonight, an isolated +3.2 is not strong evidence of anything. Treat it as a
  hint, not a handle.

---

## E. RANKED FRONTIER FOR THE NEXT RUN (replaces §7 of PK_CONTEXT.md)

Of the old §7 list: item 1 (PK10 two-word products) is **finished**; item 2 (periods 25–72) was
worked and superseded by the period scan to 100; item 3 (three-word products) is **run** on all
three targets; item 4 (Gromark) is **Tier 2 for digit primers** (§F12); item 5 (dual beam) was in
flight at write-up; item 6 (PK9→PK8 coupling) is **run** (§F5). What follows is re-ranked by what
is actually left.

### 0. Read §A0 first. Then work PK10, not PK8 or PK9.

The single most actionable result of the night: ranking searches over ~30,000 candidates are below
their own noise floor at 144–153 letters, and **no amount of compute changes that**. A genuine
two-word product key scores z ≈ 6 at those lengths against a noise ceiling of 7.8–7.9; the same key
at 504 letters scores 15.57 against a ceiling of 6.75 and wins the grid outright. Blind Hill fires
6/6 at n=504 and 2/6 at n=144. Gromark's own control makes the point most sharply: at n=144 the
null best-of-search over 10⁷ primers already reaches IoC 0.0628 on *shuffled* text, so the search
size alone manufactures apparent-English IoC.

So effort on PK8 and PK9 belongs in tests whose false-positive rate is set by **exact algebra**, not
by ranking a candidate list — the crib/consistency family, which detects a correct hypothesis with
probability 1 at any length. Or solve PK10 first and use it as the lever the setter says exists.

### 1. Crib with a columnar underneath — validated on the real PK4, the engineering is specified

This is now the top item because it is the one *exact* test with a known gap, and exact tests are
what work at short lengths.

`crib_transpo.py` recovers PK4's true column order **[6,4,1,2,5,3,0,7] as the unique pass out of all
40,320 permutations**, from a 24-letter crib, at a false-positive rate of 2.7 × 10⁻¹⁶. The attack
works. What blocked it was cost: W=9 means 362,880 permutations × 48,616 cribs.

**The engineering that unblocks it, specified.** The consistency condition `R·K = 0` is linear and K
decomposes by column, `R·K = Σ_c R_c · K_{c,slot(c)}`, so the permutation search is a **meet in the
middle** — enumerate ordered 4-subsets (3,024) and ordered 5-subsets (15,120), hash the partial
sums, match on (complementary slot set, negated sum). 362,880 collapses to ~18k per crib-structure,
about 20 ms, so the whole corpus × a dozen structures is a couple of minutes. One wrinkle: R depends
on the permutation unless every key period divides the column length, so either restrict to those
structures or cache R by residue signature. The permutation-free special case is already run (§F1).

### 2. Three-word and deeper products on PK10 only

The (length, modulus) grid covers products of **any** arity — the score for one factor depends on the
others only through their lcm (§F6) — and at n=504 it sees 92% of three-word and 58% of four-word
length-sets. PK8/PK9 versions are run but Tier 3 by §A0 and not worth repeating. Extend PK10's grid
to more key alphabets and to moduli above 84 by accepting smaller classes with more nulls.

### 3. Gromark's three open corners (§F12)

In the agent's own priority order: (ii) the mix-**after**-shift ACA form at PK8/PK9 lengths, which
needs a joint primer + mixed-alphabet solve (~5 h single-core for the full grid, and it is the only
test that can see that form at n=144); (i) full 26⁷ mod-26 letter-primer enumeration (~12–20 h,
26⁸ is out of reach); (iii) a transposition applied *on top of* the Gromark, outside every statistic
used so far. Do **not** re-run mod-10 digit primers at L ≤ 8, or dictionary-word primers 5–14.

### 4. Non-additive block ciphers beyond what was run

Blind Hill k = 2, 3, 4 with additive offset periods 1–6 is done and **Tier 2 for PK10** (§F2). Open:
a Hill stage with a longer additive period, or an additive that is itself a two-word product —
design law 2 applied to PK7's construction — and non-Hill non-additive constructions generally.
PK10's statistical signature (IoC 0.0388, census LLR −13.03) remains closely matched by Hill 3×3
(−15.93) and Hill 4×4 (−13.88), so the family is still a priori attractive even after the negative.

### 5. Running key through an independent keyed alphabet

The census argument (§A6) excludes an English key text read in the *same* tableau as the plaintext,
which is what PK5 does. It does **not** exclude one read through an independent keyed alphabet:
averaged over 400 random alphabet permutations the hypotheses separate by only 1.0 σ on PK10. Since
PK3 proves this setter builds keys by encrypting one word under another, a key text pushed through a
keyed alphabet is squarely in style, and §6's running-key screen tested specific *texts*, not the
*mapping*.

### 6. PK9 → PK8, once PK9's own construction is known

The derivation is sound and the machinery exists (§F5): if PK8's key is PK9's plaintext then
`d = c8 − c9` is PK8's plaintext under PK9's keystream. All 48 derived texts have had a period scan,
a product grid and the full crib sweep — nothing. This stays live but is **blocked on PK9**, not on
compute. Same for a Gromark whose primer derives from PK9's plaintext.

### 7. Do NOT re-run

* Any periodic substitution on PK10 with period ≤ 100, in **any** alphabet. The column-IoC statistic
  only needs the key constant within a column, so it covers Vigenère, Beaufort, variant, Gronsfeld,
  Porta, and **all four Quagmires with any keyed alphabet**, with or without an inner columnar —
  a much wider net than §6's four pairings.
* Two-word dictionary product keys on any of the three, lengths 3–16.
* Cribs at fixed positions with no transposition — ~797 million exact tests, zero passes.
* **Mid-text cribs.** Bounded on principle (§F11): the longest verbatim substring shared between any
  two of the seven known plaintexts is 14 letters, too short to constrain the relevant structures.
* Gromark mod-10 digit primers at L ≤ 8 under the four recurrences tested.
* Beaufort mode when scoring by class IoC — it is arithmetically identical to subtract (§F7).

## F. LATE RESULTS (jobs that finished after §A–E were drafted)

### F1. Permutation-free crib test for "columnar of width W, key period dividing the column length"

If W divides n and the key period divides the column length L = n/W, then the key at ciphertext
position s·L+t depends only on t, not on which column landed in slot s. So for every t the W
ciphertext letters {ct[s·L+t]} must be a **shifted copy, as a multiset**, of the W crib letters
{crib[c+W·t]} — and the induced column matchings must agree across all t. No W! search at all.

Controls: fires on synthetic instances at (n,W) = (153,9), (144,9), (504,9), (144,8), (504,7), each
with a unique shift per t. Matched null: **0 of 32,000** random cribs pass.

**Executed: 1,000,200 tests** — 10,685 cribs × widths {3,9,17} on PK8, {2,3,4,6,8,9,12,16,18,24} on
PK9, {2,3,4,6,7,8,9,12,14,18,21,24} on PK10 × 2 alphabets × 3 modes. **Zero passes.**
Tier 2 within its stated shape.

### F2. Blind Hill row recovery, k = 2, 3, 4, offset periods 1–6

Frontier item 1, run rather than merely proposed. For a decryption row r, the sequence
s_b = r·c_b over blocks is a shifted copy of every k-th plaintext letter when r is a true row, so
its IoC is English and the offset never has to be guessed. **Degenerate rows are excluded**
(gcd(r₁…r_k, 26) > 1 collapses the output alphabet and inflates IoC for free — that is exactly the
z=+5.78 false lead recorded in §6), and the matched null applies the identical exclusion.

Control on the **real PK7** (Hill 3×3, inverse spells ALCHEMIST, offsets period 2): the true rows
[10,16,3], [8,9,0], [9,11,15] score IoC 0.0768 / 0.0681 / 0.0617 at ranks **3, 24, 100 of 15,372**,
z = +6.2 / +4.7 / +3.5. (Ranks 1–2 are scalar multiples of the true row — u·r for u coprime to 26
gives a bijection of the same sequence, hence identical IoC.)

**END-TO-END POWER CONTROL — the sweep was run unchanged on PK7 itself.** It fires **above
ceiling in 7 of 10 cells**, including the correct P=2 at z = +6.21, and the winning row [2,24,11] is
exactly 21 x [10,16,3] mod 26 — the true row's scalar-equivalence class. So this sweep detects the
one Hill cipher in the series, from its published ciphertext, blind.

| target | cells | row-evaluations (+ nulls) | above matched ceiling |
|---|---|---|---|
| **PK7 (control, n=279)** | 10 | 153,720 | **7** |
| PK8 (153) | 10 (k=3 only; 153 is divisible by neither 2 nor 4) | 153,720 | **0** |
| PK9 (144) | 30 (k=2,3,4) | 4,442,760 | **0** |
| PK10 (504) | 30 (k=2,3,4) | 4,442,760 | **0** |

**Power by message length** (blind Hill 3×3, P=2, fires above its own ceiling on synthetic Hill
ciphertexts):

| n | fired |
|---|---|
| 279 (PK7's length) | **6/6** |
| 504 (PK10) | **6/6** |
| 153 (PK8) | 3/6 |
| 144 (PK9) | 2/6 |

So: **PK10 — Tier 2, not a Hill cipher of dimension 2, 3 or 4 with an additive offset of period
≤ 6.** PK8 and PK9 — **Tier 3**, same search, but the test only fires about half the time at those
lengths (§A0 again). That closes what §E ranked as frontier item 1 for PK10 and leaves it ajar for
the other two. What remains open
in the family is a Hill stage with a longer additive period, or an additive that is itself a
product of words (design law 2 applied to PK7's construction), and non-Hill non-additive
constructions generally. Raw output in `results/hillblind_*.json`.

### F3. PK9's two "anomalies" are one anomaly — an identity worth carrying forward

IoC = (Σnₓ² − n)/(n(n−1)) and χ² against uniform = (26/n)·Σnₓ² − n are **affine transforms of each
other**: both are functions of Σnₓ² alone. Verified numerically — predicting χ² from IoC alone
reproduces 29.00 / 47.39 / 29.00 exactly for PK8 / PK9 / PK10.

So PK9's "IoC z = +3.24" and its "census χ² = 47 on 25 df" are the *same observation reported
twice*, not two independent lines of evidence. Its real weight is one-sided p ≈ 0.004 on a single
target, ≈ 0.012 after the three-target multiplicity — and after the number of statistics computed
tonight, that is a hint and nothing more. The individual letter extremes are unremarkable: the
maximum count of 13 has P ≈ 0.098 under a uniform null, the minimum of 1 has P ≈ 0.48.

Practical consequence for the next session: **IoC carries no positional information whatsoever**
(it is permutation-invariant, hence a pure function of the letter census). It is superb as a
transposition-invariant *scoring* function once a key hypothesis is peeled off, which is how it is
used throughout this run — but a raw ciphertext IoC can never, by itself, indicate a period or any
other positional structure. PK_CONTEXT §5 lists the two as separate calibration constants; they
are not.

### F4. Direct structural inspection — nothing hiding in the raw text

Worth recording because it is cheap and rules out a whole class of "look at it differently" ideas.

* **No repeated substring of length ≥ 4 within PK8, PK9 or PK10.** Across all ten ciphertexts the
  only length-5+ repeat anywhere is `THTEO` (PK2 at 30, PK7 at 152) — a coincidence between two
  already-solved puzzles. High-entropy keystreams, as expected.
* Read as a 9-column grid, no row, column, diagonal or every-k-th reading produces anything
  legible for any of the three.
* Positional letter agreement between pairs of targets is at chance: PK8/PK9 4 matches (null
  5.37 ± 2.23, z −0.61), PK8/PK10 9 (5.70 ± 2.31, z +1.43), PK9/PK10 8 (5.45 ± 2.27, z +1.12).

### F5. The PK9 → PK8 coupling, attacked properly (frontier item 6)

Design law 4 says PK5's key is PK4's plaintext, and the setter says PK9 unlocks PK8. If **PK8's key
is PK9's plaintext**, then for i < 144

    p8[i] = c8[i] − PT9[i]  and  PT9[i] = c9[i] − K9[i]   ⇒   p8[i] = (c8[i] − c9[i]) + K9[i]

so `d = c8 − c9` is PK8's plaintext enciphered under PK9's own keystream, and PK9's plaintext never
has to be known. Note also that a 144-letter key on a 153-letter message has **period 144, which no
period scan can reach** — this route and the wrap-crib test in §D are the only ways to see it.

**48 derived texts** were built: every ordered pair of PK8/PK9/PK10 × both alphabets × forward and
reversed × both signs. Each got:

* a transposition-invariant period scan **with a power curve** — best result anywhere was
  pk8−pk9R_AZ at p=23, z=+3.76, in a cell where a *true* period-23 cipher gives only +3.2 and the
  power is 0.53, i.e. the observation exceeds what the real thing would produce, which is the
  signature of noise, not signal. Across 48 texts × ~30 periods ≈ 1,440 tests, +3.76 is at
  expectation.
* a two-word product grid — best (z − matched null max) anywhere was +2.62, with unrelated top words.
* **the crib × key-structure consistency sweep: 367,133,184 effective tests, expected false
  positives 4.12, observed passes 0.**

Tier 3 overall (the period scans are weak at 144 letters, per §A0), but the crib component is
exact and therefore fully powered: **no crib in the corpus, under any of the 404 key structures,
describes any of the 48 coupling texts.**

### F6. What the (length, modulus) grid actually covers — products of any number of words

The decomposition generalises past three factors. For a key `k[i] = Σ_f u_f[i mod p_f]`, peeling the
length-a factor makes every residue class mod **lcm(all the other periods)** monoalphabetic. The
score for a length-a word therefore depends on the other factors *only through their lcm* — so one
(length, modulus) grid tests two-word, three-word, four-word and deeper products at once. The
limit is that the modulus M must satisfy n/M ≥ ~5–6 for the class IoC to be measurable at all.

Coverage, counting distinct length-sets drawn from lengths 3–16 for which *some* factor has the
others' lcm inside the cap (and does not divide it, which would leave no signal):

| | PK10 (cap M ≤ 84) | PK8 (cap M ≤ 30) | PK9 (cap M ≤ 28) |
|---|---|---|---|
| two-word (91 sets) | **91 (100%)** | 91 (100%) | 91 (100%) |
| three-word (364 sets) | **334 (92%)** | 225 (62%) | 198 (54%) |
| four-word (1,001 sets) | 576 (58%) | 209 (21%) | 143 (14%) |

This is a coverage statement about which *length-sets* the method can see at all, and is separate
from the §A0 power question — on PK8 and PK9 the ranking power is the binding constraint regardless.
For PK10 the grid sees essentially the whole two- and three-word space.

### F7. Two corrections to my own product grid, found by controlling the modes

* **All three modes work.** `sub`, `add` and `beaufort` were each validated by encrypting a
  synthetic in that mode and confirming recovery: at n=504 the true keys come back at rank 1 with
  z = +10.3 to +15.6 in all three; at n=153 at ranks 1–3. A mismatched mode fails as it should
  (scoring a `sub` ciphertext with `add` puts OCHRE at rank 3,462 of 38,208).
* **But `beaufort` is redundant with `sub` under this statistic**, and exactly so: within a residue
  class the beaufort residual is `const − c` where the subtract residual is `c − const`, and IoC is
  invariant under negation as well as shift. Checked against the stored results: **680 of 680
  sub/beau cell pairs agree to 1e-9 on all three targets.** So the "2,040 cells" figure quoted
  throughout is **1,360 distinct searches**. No verdict changes — the matched null was computed from
  the same cells, so the ceiling absorbs the duplication — but the next session should not spend a
  third of its compute on beaufort while scoring by class IoC.

The crib sweep has the mirror-image redundancy, in the other mode: there `add` gives K = −K_sub, and
a product structure is **closed under negation** (if k[i] = Σ u_f[i mod p_f] then −k[i] = Σ (−u_f)[i
mod p_f]), so the consistency verdict is identical. Verified: K_add = −K_sub on all 400 test cribs,
and the verdict matched in **2,000 of 2,000** structure tests. `beau` (K = C + P) *is* a distinct
search there. So the crib sweep's 54,208,692 tests are ≈ 36.1 million distinct ones and its expected
false-positive count drops from 0.67 to ≈0.45 — the observed count is 0 either way.

The general lesson for the next session: **check whether your modes are actually distinct under the
statistic you are scoring with.** Two of the three modes collapsed in each of the two biggest sweeps
here, in opposite directions, for reasons specific to each statistic.

### F8. The enriched crib corpus — 48,616 cribs, 356 million tests, zero passes

§A0 establishes that at 144–153 letters ranking searches are below their own noise floor while the
crib × key-structure test keeps full power at any length. That makes the crib corpus, not compute,
the binding constraint on PK8 and PK9 — so it was enlarged 4.5× with a richer generative grammar in
the diary's voice: elapsed-time openings over 44 numerals × 25 time units × 37 continuations,
ordinal forms, subject × verb × object sentences built from the story's own nouns (the needle, the
whitesmith, the archive, the knot, the inner door, Pellegrin), and 25 literal continuations of PK7's
closing line, each padded with numerals.

**Executed: 355,980,204 effective tests** — 48,616 cribs × 404 key structures × 3 targets × 2
alphabets × 3 modes × {prefix, suffix}; 104,004 underpowered structure/length combinations skipped
and counted. **Expected false positives 3.20. Observed passes: 0.**

Combined with §A8, §F1, §F5 and the wrap-crib test, the crib family now stands at roughly
**780 million exact tests with zero passes**, and every one of those tests would have fired with
probability 1 on a correct crib. The remaining ways this family can still be wrong are worth stating
plainly: the true opening is not in the corpus; the plaintext is not in English (PK2 contains
Italian, and §6 records that Italian keys and alphabets were screened but not Italian *plaintext*
against cribs); the crib sits at neither end; or a transposition scatters it in a way §F1's
permutation-free case does not cover and §E item 3's meet-in-the-middle has not yet been built.

### F9. End-to-end control of the crib pipeline on a REAL puzzle — the strongest one available

Every earlier crib control fed the solver a crib taken from a known plaintext. This one does not:
it asks whether the **corpus generator, keystream derivation and structure-consistency test working
together** recover a real puzzle.

PK1's true opening is `INVESTIGATIONLOGITEMEIGHT`. The generator produces it independently — it
falls out of the `INVESTIGATIONLOGITEM` + numeral pattern, which is in the corpus because PK1's own
opening suggested the pattern, not because the answer was inserted. Running the pipeline on the
**real PK1 ciphertext** with that crib returns:

* period **10** — PK1's true period (Quagmire III on KA, key PROVENANCE) — at a false-positive rate
  of **5.96 × 10⁻²²** for the 25-letter crib;
* period 20, which is correct rather than spurious: a period-10 key is trivially also period-20;
* pairs (3,10), (4,10), (5,10), (6,10) — again all containing the true period;
* and the 20-letter prefix `INVESTIGATIONLOGITEM` alone already returns period 10 at 7.1 × 10⁻¹⁵.

So the whole chain works on a real puzzle of this series. This is now control #8 in `verify.py`.
It materially strengthens every crib negative in this document: the ~780 million zero-pass tests
were run by a pipeline demonstrated to recover a genuine key structure from a genuinely generated
crib.

### F10. Three-word product grids

| target | cells | word-evaluations | wall | observed max z | matched ceiling | cells beating own null | verdict |
|---|---|---|---|---|---|---|---|
| PK9 | 2,688 | **317,784,240** | 1,617 s | 7.24 | 7.29 | 434 / 2,688 (chance ~448) | below ceiling, nothing |
| PK8 | 2,796 | **329,959,512** | 1,716 s | 7.07 | 8.03 | 499 / 2,796 (chance ~466) | below ceiling, nothing |

Top cells are the usual noise signature — orthographically unrelated words (CREUTZFELDT,
DOMESTICATE, PLEISTOCENE; BREWMASTERS, GANGMASTERS, BANDMASTERS) rather than a true key with its
near-misses stacked beneath it. Per §A0 this is a **Tier 3** screen at PK9's length regardless of
the z, and per §F6 the grid sees 54% of three-word length-sets at n=144. PK8 and PK10 still running
at write-up; see `logs/p3_pk8.log` and `logs/p3_pk10.log`.

### F11. Cribs at every offset — run, and then bounded on principle

§A8 and §F8 tested cribs only at the two ends. The series repeats phrases across entries, so a
recurring phrase could sit anywhere, and the consistency test does not care where a crib sits — only
that its positions are known.

**A simplification found while building this, worth keeping:** the constraint matrix R depends only
on **(crib length, structure)**, not on the offset. Shifting a contiguous crib permutes which
unknown `u_f[j]` each row uses, but the pattern of *which rows share an unknown* is shift-invariant,
so the left null space is unchanged. Verified over 240 (structure, length, offset) comparisons with
zero mismatches. One checker therefore serves every offset and the whole offset scan collapses to a
single matrix product per (crib, structure) — the sweep went from hours to 15 seconds.

Control: planting `THEGUTTERALONGTHEWALL` in PK6's plaintext enciphered under PK6's real key PORTAL,
the sweep locates it at **exactly offset 71** with PK6's true period 6 and its multiple 12. (This
omits PK6's double columnar, which no crib method can cross — that is the family's known limit, not
a flaw in this control.)

**Executed: 16,525,920 tests** — 47 curated recurring phrases from the series (including the Italian
quotation from PK2) × every position × 3 targets × 2 alphabets × 2 modes × 334 structures.
Expected false positives 0.19. **Observed passes: 0.**

**Then the family was bounded rather than scaled.** Before extending this to ~12,000 substrings of
the known plaintexts, I checked whether this author repeats long phrases at all. He does not: the
**longest verbatim substring shared between any two of the seven known plaintexts is 14 letters**
(`STHEWHITESMITH`), and all nine cross-entry repeats of length ≥12 are variants of THEWHITESMITH.
A 14-letter crib is too short to constrain the structures that matter — against a (5,9) product it
has 14 unknowns for 14 equations, so zero degrees of freedom. **Mid-text cribs are therefore a dead
avenue on principle, not merely unproductive**, and the ~3 CPU-hours that scan would have cost were
not spent. The productive crib position is the opening, which is what §A8 and §F8 target.

### F12. Gromark and generated keystreams (frontier item 4) — Tier 2 for digit primers, verified independently

Run as a parallel work stream, with a purpose-built C kernel. **Executed: 2,032 real search cells
plus 4,012 matched-null cells, 5,700 s, 1.235 × 10¹⁰ trial decryptions** — *all* 10⁷ primers at
L=7 and *all* 10⁸ primers at L=8, enumerated rather than sampled, crossed with four recurrences
(k[i]=k[i−L]+k[i−L+1] the ACA standard, k[i]=k[i−L]+k[i−1], k[i]=k[i−1]+k[i−2],
k[i]=k[i−L]−k[i−L+1]), both text alphabets, both addition directions, two statistics.

Controls: the true primer comes back at **rank 1 among 10⁸ candidates** at all three message
lengths (z = +18.8 / +19.7 / +44.2), and still rank 1 with a width-9 columnar underneath
(z = +57.2), which is what establishes transposition-invariance rather than assuming it.

Two limits the agent stated against its own interest, both worth carrying:
* the `k[i]=k[i−1]+k[i−2]` recurrence is structurally degenerate — past position L the keystream
  depends only on the last two primer digits — so the exact primer is *not* recoverable. It verified
  the search still recovers the **keystream** (matching the truth 137/137 and 497/497 positions past
  the primer window), so that recurrence is covered only up to an equivalence class.
* the true ACA form `C = MIX[(P+k)]`, with the mixed alphabet applied *after* the shift and unknown,
  is invisible to the shift-IoC statistic. The within-key-class statistic recovers it at n=504 but
  has **no power at n=144/153** — the same length problem as §A0.

**Above-ceiling autopsy, verified independently by me.** 39 of 2,032 cells exceeded their pooled
matched-null max, against 35.6 expected by chance. The top hit was pk9, L=7, primer 2546754,
IoC 0.063714 vs a pooled null max of 0.06284 — an English-looking IoC at n=144. I rebuilt it from
scratch with my own code rather than the agent's kernel, **reproduced IoC 0.063714 exactly**, and
ran my own monoalphabetic hill-climb on the residual: **−5.649, against shuffled-copy nulls of
−5.602 to −5.718**. Indistinguishable from noise, and nowhere near English's −4.25. If a primer were
right the residual would be a monoalphabetic image of the plaintext and would climb to English; it
does not. Chance, confirmed independently. The decisive scale check: the positive control's *true*
primer scored 0.0757 at this length with z = +18.8, while the null best-of-search at 10⁷ primers
already reaches 0.0628 on shuffled text — at n=144 the search size alone manufactures apparent
English IoC.

**Verdict: Tier 2** for mod-10 digit primers at L=7 and L=8 under those recurrences, alphabets and
directions, by exhaustion rather than sampling. **Three corners stay open**: (i) mod-26 letter
primers were screened only over dictionary words — 26⁷ = 8×10⁹ was not enumerated (Tier 3);
(ii) the mix-after-shift sub-form at PK8/PK9 lengths; (iii) a transposition applied *on top of* the
Gromark, which breaks keystream alignment and lies outside every statistic used.
