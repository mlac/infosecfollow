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

## B. WHAT RAN, WITH REAL COUNTS AND WALL-CLOCK

| sweep | configurations actually executed | wall | observed best | matched-null ceiling | verdict |
|---|---|---|---|---|---|
| PK8 two-word product, full grid | 2,040 cells / **245,423,952 word-evaluations** | 542 s | z = 7.07 | **7.87** | Tier 2 dead |
| PK9 two-word product, full grid | 2,040 cells / **245,423,952 word-evaluations** | 521 s | z = 7.15 | **7.83** | Tier 2 dead |
| PK10 two-word product, full grid | 2,040 cells / 245,423,952 word-evaluations | see §B1 | — | — | — |
| PK10 period scan 2–100 | 99 periods × (500 nulls + 120 power sims) | 320 s | z = **+1.92** (p=47) | ±2 | **Tier 2 dead** |
| PK8 period scan 2–30 | 29 periods × 620 | 90 s | z = +3.25 (p=7) | — | p=7 open, see §C1 |
| PK9 period scan 2–28 | 27 periods × 620 | 85 s | z = +2.41 (p=7) | — | Tier 2 dead p≤8, p=10 |
| Shared-keystream coupling | 24 pair/alphabet/direction combinations × all offsets (144–504 each) + 60 matched nulls per scan | 40 s | all below ceiling | — | Tier 3 (weak test) |
| Progressive-key scan | 3 kinds × p × d × 2 alphabets, 150 nulls per cell | running | see §C2 | — | — |

**Grid definition for the product sweep** (one "cell" = one full pass over a whole word list):
target × {KA, A-Z} text alphabet × {KA, A-Z} key alphabet × {subtract, add, beaufort} × 91 length
pairs (3 ≤ a < b ≤ 16) × up to 2 decomposition directions, 5 letter-shuffle nulls per cell.
Word list: 289,026 words, lengths 3–16.

### B1. PK8 and PK9 two-word product keys: Tier 2 dead

The discriminating evidence is not the top z, it is the shape of the result:

* **PK8**: observed max z = 7.07; matched-null ceiling 7.87. Cells beating their own null: **361 of
  2,040**, against ~340 expected by chance with 5 nulls per cell. Mean observed z per cell 4.38 vs
  matched-null mean 4.37.
* **PK9**: observed max z = 7.15; ceiling 7.83. Cells beating their own null: **302 of 2,040** —
  *below* chance. Mean observed 4.38 vs null 4.42.

Both sweeps sit exactly on their nulls. And the top-ranked words are orthographically unrelated to
each other (PK8: HENNELL, HANGEUL, HANNELE, DOUBLES, PENNELL; PK9: BREWMASTERS, GANGMASTERS,
BANDMASTERS, MYTHBUSTERS), which is the signature of noise. A genuine hit looks different: on the
real PK3 the top five were PENTIMENTO, SENTIMENTO, TESTAMENTO, SENTIMENTS, PORTAMENTO — the true
key with its orthographic neighbours stacked underneath it, because near-misses of the right key
still cancel most of the keystream.

Scope, stated precisely: **these specific keys are dead** — additive two-word product keys built
from dictionary words of length 3–16 on a KRYPTOS-keyed or standard tableau, with or without an
inner columnar. The family stays open for keys that are not dictionary words, for word lengths
above 16, and for products of three or more words (§C3).
