# Paradigm Kryptos CTF — PK8 / PK9 / PK10 working directory

Results and verdicts live in **`OVERNIGHT_RESULTS.md`**. Start there.
To re-establish trust in everything here in one command:

```
OMP_NUM_THREADS=1 python3 verify.py     # 8 positive controls, ~3 min
```

If any control fails, every negative in OVERNIGHT_RESULTS.md is void.

## Setup
```
pip install numpy wordfreq
python3 build_model.py     # quadgrams.npy  (~2 min)
python3 rebuild_dict.py    # words.txt, 289,026 words — the 200k list is NOT enough, see below
python3 controls.py        # all seven solved puzzles must round-trip
```

## Core library
| file | what it is |
|---|---|
| `lib.py` | ciphertexts, the 7 solved plaintexts, KRYPTOS alphabet, `col_enc/col_dec`, `q3enc/q3dec`, `ioc`, quadgram scoring |
| `controls.py` | the seven round-trip controls; run after any change to `lib.py` |
| `verify.py` | all positive controls for every solver in this directory |
| `build_model.py` / `rebuild_dict.py` | quadgram model and word list from `wordfreq` (no network needed) |

## Solvers (each has a positive control that passes)
| file | attack | control it recovers |
|---|---|---|
| `product2.py` | two-word product keys, decomposed (N_a + N_b, not N_a × N_b) | PENTIMENTO+ORDINATE from real PK3; OCHRE+VERDIGRIS from real PK4 |
| `product3.py` | three-word products; the score depends on b,c only via lcm(b,c) | OCHRE×VERDIGRIS×ANNEAL on a 504-letter synthetic |
| `period_scan.py` | transposition-invariant period exclusion **with a power curve** | synthetic period-p at each length |
| `mutual_ioc.py` | transposition-invariant *solver* for a periodic key (histogram alignment) | — |
| `progressive.py` | progressive / sliding keys (aperiodic, so period scans are blind) | synthetic block/letter/quadratic progressions |
| `outer_transpo.py` | substitute-**then**-transpose architecture | synthetic |
| `crib.py`, `crib_sweep.py` | crib → keystream → key-structure consistency over GF(2)×GF(13) | PK3's (8,10) and PK1's period 10; 0 false passes in 42,200 nulls |
| `crib_transpo.py` | crib with a columnar underneath | **real PK4's column order, unique of 40,320** |
| `crib_multiset.py` | permutation-free crib test when the key period divides the column length | synthetics; 0 of 32,000 null cribs |
| `wrap_crib.py` | a key shorter than the message — invisible to every period scan | — |
| `hill_blind.py` | blind Hill row recovery, k=2,3,4, degenerate rows excluded | **real PK7's rows at ranks 3/24/100 of 15,372** |
| `derived.py` | PK9→PK8 coupling texts (d = c8 − c9 is PK8's plaintext under PK9's keystream) | — |
| `keytype.py` | which key type the ciphertext IoC is consistent with, simulated per length | — |

`results/*.json` holds each sweep's output. The bulky raw dumps (`product2_*`, `progressive_*`,
`gromark_words_*`, `lp_*_raw*` — about 19 MB) and the regenerable inputs (`words.txt`,
`quadgrams.npy`, `cribs_big.txt`, `logs/`) are gitignored: every conclusion drawn from them is in
`OVERNIGHT_RESULTS.md` and each is reproducible by re-running the script named beside it there.
The summaries and autopsies that carry the evidence *are* tracked.

## Two traps this directory exists to stop you re-entering
1. **`wordfreq.top_n_list('en', 200000)` is too small.** It yields 183,150 words and does not
   contain PENTIMENTO or WHITESMITH — a sweep on it could not have found PK3's own key. Use
   `rebuild_dict.py` (289,026 words).
2. **Undersized nulls manufacture hits.** PK8's period-7 mutual-IoC score was "above ceiling" at 25
   and at 200 shuffle-nulls. At 2,000 the null maximum equals the observed value exactly. Size the
   null to the search, then autopsy anything that survives.
