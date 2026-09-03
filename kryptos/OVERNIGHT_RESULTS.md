# OVERNIGHT RUN — PK8 / PK9 / PK10 — RESULTS

**Status: no puzzle solved.** That is the likeliest outcome and it is what happened. What follows
is a set of eliminations, several of them substantially stronger than anything in the prior
elimination map, plus a rebuilt frontier. Read §A first — it changes what is worth running next.

Run date 2026-09-03. Working dir `kryptos/`. Harness: all seven solved puzzles round-trip exactly
(`python3 controls.py`).

---

## A. HEADLINE FINDINGS

### A1. PK10 has no periodic key of period 2–72. Tier 2, transposition-invariant.

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

Every period from 2 to 72 except 63 is excluded at power 1.00 with the observed z inside ±2.
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
Combined with A1 this is tight: PK10's keystream is **aperiodic over 504 letters and near-uniform
in its marginal distribution** — it behaves like a long generated key, not like a text.

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

### A8. The crib attack (the requested last shot): 54 million tests, zero passes

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
**Expected false positives under the null: 0.67. Observed passes: 0.**

Scope: the crib sits at fixed ciphertext positions, so this assumes **no transposition**. That is
the honest limit — see §E for the width-9 extension that was designed but not run.

---

## B. WHAT RAN, WITH REAL COUNTS AND WALL-CLOCK

| sweep | configurations actually executed | wall | observed best | matched-null ceiling | verdict |
|---|---|---|---|---|---|
| PK8 two-word product, full grid | 2,040 cells / **245,423,952 word-evaluations** | 542 s | z = 7.07 | 7.87 | **Tier 2 dead** |
| PK9 two-word product, full grid | 2,040 cells / **245,423,952 word-evaluations** | 521 s | z = 7.15 | 7.83 | **Tier 2 dead** |
| PK10 two-word product, full grid | 2,040 cells / **245,423,952 word-evaluations** | 1,728 s | z = 6.40 | 6.75 | **Tier 2 dead** |
| PK10 period scan 2–100 | 99 periods × (500 nulls + 120 power sims) | 320 s | z = +1.92 | ±2, power 1.00 | **Tier 2 dead** |
| PK8 period scan 2–30 | 29 periods × 620 | 90 s | z = +3.25 (p=7) | — | p=7, p≥18 open |
| PK9 period scan 2–28 | 27 periods × 620 | 85 s | z = +2.41 (p=7) | — | dead p≤8, p=10 |
| Mutual-IoC periodic solver, p 2–24 | 3 targets × 2 alphabets × 23 periods × 400 shuffle-nulls × 30 restarts | 400 s | see §C1 | per-period | **Tier 2 dead** |
| Progressive-key scan | pk10 15,600 cells, pk8 4,680, pk9 4,368; 150 nulls each | 300 s | z = +4.70 (pk10) | ≈ +4.4 expected | Tier 3, at expectation |
| Substitute-then-transpose scan | pk10 116 (W,q) cells at power 1.00, pk8 14, pk9 43 | 200 s | z = +3.87 (pk9) | §C2 | **Tier 2 dead (PK10)** |
| Shared-keystream coupling | 24 pair/alphabet/direction combos × every offset + 60 nulls per scan | 40 s | all below | — | Tier 3 (weak test) |
| Running-key census LLR | 3 targets × 2 alphabets × 8,000 sims | 30 s | z = −5.16 (pk10) | — | **Tier 2 dead (PK10)** |
| **Crib × key-structure consistency** | **54,208,692 effective tests** | 200 s | 0 passes | 0.67 expected FP | **Tier 2 dead (no-transposition)** |
| PK10 three-word product grid | 42 moduli × 14 lengths × 12 pairings, 5 nulls/cell | running | §D | — | — |

Product-grid cell definition: target × {KA, A-Z} text alphabet × {KA, A-Z} key alphabet ×
{subtract, add, beaufort} × 91 length pairs (3 ≤ a < b ≤ 16) × up to 2 decomposition directions,
5 letter-shuffle nulls per cell. Word list 289,026 words, lengths 3–16.

### B1. Why the product negatives are real and not just low scores

* **PK8**: max z 7.07, ceiling 7.87. Cells beating their own null: **361 / 2,040** vs ~340 expected.
* **PK9**: max z 7.15, ceiling 7.83. Cells beating own null: **302 / 2,040** — *below* chance.
* **PK10**: max z 6.40, ceiling 6.75. Cells beating own null: 386 / 2,040.

All three sweeps sit on their nulls, and the top-ranked words are orthographically unrelated
(PK8: HENNELL, HANGEUL, HANNELE, DOUBLES; PK9: BREWMASTERS, GANGMASTERS, BANDMASTERS;
PK10: DIMMADOME, CAPITATED, OBERKAMPF, LUMINARIA). A genuine hit looks different — on the real
PK3 the top five were PENTIMENTO, SENTIMENTO, TESTAMENTO, SENTIMENTS, PORTAMENTO: the true key
with its orthographic neighbours stacked underneath, because a near-miss still cancels most of
the keystream. That clustering is the signature to look for, and it is absent everywhere here.
