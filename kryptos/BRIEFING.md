# AGENT BRIEFING — Paradigm Kryptos CTF, PK8/PK9/PK10

Working dir: `/home/user/infosecfollow/kryptos`. ALWAYS `cd` there and `sys.path.insert(0,'.')`.

## Assets already built and VERIFIED — use them, do not rebuild
- `lib.py` — KA=`KRYPTOSABCDEFGHIJLMNQUVWXZ`, `CT` (all 10 ciphertexts), `PT` (the 7 solved
  plaintexts), `col_enc/col_dec`, `q3enc/q3dec`, `ioc`, `ioc_rows`, `qscore`, `qscore_rows`,
  `to_idx/to_str`, `ka_to_az`.
- `controls.py` — all seven solved puzzles round-trip exactly. Run it if you touch lib.py.
- `quadgrams.npy` — log10 quadgram model, A-Z index order. English = -4.25, random = -8.23.
- `words.txt` — 183,150 uppercase English words (wordfreq top 200k). Sizes by length:
  3:9534 4:16578 5:23452 6:28012 7:27894 8:24081 9:18934 10:13713 11:8819 12:5257 13:3061 14:1545
- `product2.py` — the two-word product-key decomposition solver (`score_words`, `wordmat`,
  `to_idx`, `load_words`, `pairs`). Validated: recovers OCHRE x VERDIGRIS at rank 1/1 on a
  504-letter synthetic.

## CALIBRATION (confirmed on this build)
IoC random 0.0385 | English 0.0647 | Italian 0.0744 | English n=144 mean .0640 (p5 .0562 p95 .0728)
| English n=504 mean .0643 (p5 .0602 p95 .0684) | quadgram/letter English -4.25, random -8.23.
Ciphertext IoC: pk8 .0395 (z+0.6), pk9 .0445 (z+3.2 — real anomaly), pk10 .0388 (z+0.6).

## THE SEVEN SOLVED — the design grammar
PK1 Q3 on KA period 10, key PROVENANCE. PK2 columnar W7 order [1,3,4,0,5,2,6] (MARGINS).
PK3 Q3 period 40, key = q3enc(PENTIMENTO*4, ORDINATE). PK4 columnar W8 (6,2,3,5,1,4,0,7) then
Q3 period 45, key = OCHRE(5)+VERDIGRIS(9) added on KA. PK5 columnar W8 then Vigenere with
running key = PK4's PLAINTEXT. PK6 double columnar 9-wide then Q3 period 6, key PORTAL.
PK7 Hill 3x3 on KA (inverse spells ALCHEMIST) + period-2 additive (offsets spell ANNEAL).
Laws: keys are thematic words for that chapter; long keys are MANUFACTURED from short ones;
puzzles chain (PK5's key is PK4's plaintext); PK6-PK10 all have length divisible by 9.

## SETTER'S CLUES (ground truth, Dan Robinson, 10 Jul 2026)
"PK8 ... the algorithm is simple. The key has quite a lot of entropy, but some structure."
"Solving PK9 probably would help with solving PK8 ... But PK9 is harder."
=> not exotic; key is NOT a plain dictionary word; dependency runs PK9 -> PK8.

## NON-NEGOTIABLE DOCTRINE
1. MATCH YOUR NULL TO YOUR SEARCH. Every negative needs a null from running the IDENTICAL search
   on shuffled/synthetic data. Never a generic random-text baseline. Two prior false leads died
   here (a Hill row z=+5.78 that was a degenerate gcd vector; an affine z=+4.91 whose null was
   over permutations while the search ran over rotations).
2. VALIDATE THE SOLVER BEFORE TRUSTING ITS SILENCE. Before declaring a family dead, show your
   solver recovers a SYNTHETIC instance of that family at the same message length.
3. SCORE BY IoC, NOT QUADGRAMS, whenever a transposition might sit underneath. IoC is
   transposition-invariant; quadgrams are not. PK4/PK6 both put a columnar under the substitution,
   so assume one may be there.
4. AUTOPSY ANYTHING AT OR ABOVE THE CEILING: print hit positions, print the decrypt, and state how
   many tests produced the z.
5. GRADE EVERYTHING: Tier 1 impossibility / Tier 2 exhaustion within stated rules / Tier 3 screen
   (specific keys dead, FAMILY OPEN). A screen is not a verdict.
6. STANDARD OF PROOF: round-trip exactness AND a key far shorter than the plaintext it explains.
7. DO NOT FABRICATE a plaintext. DO NOT report a configuration count you did not execute.
   Negatives are the product. Report them plainly.

## ALREADY DEAD — DO NOT RE-RUN (each cost days, each had a positive control)
Tier 1: no 24/25-cell cipher (all 26 letters present); no pure transposition (census chi2
646/1071/3941 on 25df); no length-changing construction.
Tier 2: periodic polyalphabetic periods 2-24 (4 Quagmire pairings, vig/beau/variant);
sorted-profile period test p2-12; 325 thematic keyed alphabets x periods 3-14; single dictionary
key 270k EN + 183k IT words len 3-16, 4 pairings; Hill 2x2 and 3x3 with additive periods 1-3;
affine decimation P[i]=C[(a+b*i) mod n]; antipodal coupling; joint width-9 multiple anagramming
(all 9! orders); joint single-key screen 389,288 keys.
Tier 3 screens (FAMILY OPEN): running key over every sibling PT/CT + Kryptos K1-K4 + tableau, all
offsets/reversals; ciphertext-autokey lags 1-72 and plaintext-autokey with dict primers 3-16;
Gromark primers 4-6 standard recurrence; lagged Fibonacci seeds 2-4; LCG all 17576 triples; digits
of pi/e/sqrt2/phi; three-word products over a 313-term THEMATIC vocabulary only; word-constrained
dual beam (beam 45k); substitution over Playfair/fractionation; Italian words and alphabets.

## CPU DISCIPLINE
4 cores total and other sweeps are running. Set `OMP_NUM_THREADS=1`. Keep any single run under
~15 minutes; launch longer ones with `(setsid nohup python3 -u s.py > logs/x.log 2>&1 &)` and poll.
Vectorize with numpy — a pure-Python triple loop over 183k words will not finish.

## WHAT TO RETURN
Structured: what you actually executed (real configuration counts, real wall-clock), the observed
best score, the MATCHED-NULL mean and max, the Tier verdict, and a full autopsy of anything at or
above its ceiling. Write your scripts into the working dir and your findings into
`results/<name>.json` so the next session can reproduce them.
