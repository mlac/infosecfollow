import json, sys; sys.path.insert(0, '.')
R = lambda p: json.load(open(p))
out = {
 'family': ('Manufactured long keys beyond the plain two-word product (PK8/PK9/PK10): '
            'outer-repeat length != lcm, truncation/extension, concatenation, interleaving, '
            'self-encryption, alphabet-as-running-key, depth-3 recursion'),
 'role': 'ADVERSARIAL VERIFICATION of the claimed above-ceiling hits (lens: statistical)',
 'verdict': 'REFUTED',
 'headline_claim_under_test': {
   'statistic': 'IoC of the full decrypt (transposition-invariant)',
   'value': 0.06313, 'target': 'pk9', 'config': 'KA text / AZ key / sub',
   'construction': 'revtrunc14  S[i] = W[(i%14)%9] + W[8-((i%14)%9)]', 'key': 'METALHEAD',
   'claimed_z': '+8.1 (in-cell)',
   'claimed_ceiling': 'shuffle-null max 0.06070 from 2 shuffles -> flagged above_ceiling'},
 'executed_by_this_verification': {
   'xmk_null2 grid searches': 71, 'cells per grid': 696,
   'xmk_null2 cell searches': 71 * 696, 'xmk_null2 wall_sec': 2971.5,
   'xmk_cell cell searches': 3 * 201, 'xmk_cell wall_sec': 54.7,
   'xmk_null aborted after 1 replicate (cell searches)': 8 * 696, 'wall_sec': 275.9,
   'total_cell_searches': 71 * 696 + 3 * 201 + 8 * 696,
   'total_measured_solver_wall_sec': round(2971.5 + 54.7 + 275.9, 1)},
 'findings': [
  {'id': 'F1', 'title': 'The score reproduces exactly, through independently written code',
   'detail': '0.06313 / METALHEAD / revtrunc14 recomputed to 5 dp by xmk_core.search_one_ct, '
             'which rediscovers it as the argmax of the whole 696-cell grid. So do the M-B1 '
             'headlines 0.06656 (pk8) and 0.06614 (pk9). Reproduction is not the problem.'},
  {'id': 'F2', 'title': 'The decrypt is not language',
   'detail': 'quadgram -8.068/letter (random -8.23, English -4.25); one letter takes 19.4% of the '
             '144 characters and supplies 58% of the IoC. Real sibling plaintext at n=144: '
             'IoC 0.0702, top letter 14.2%, 28% of IoC, quadgram -4.30. '
             'Round-trip re-encryption is exact but VACUOUS -- the decrypt is defined as C-S, so '
             'every candidate key round-trips.'},
  {'id': 'F3', 'title': 'The +8.1 is a within-cell z, not a search z',
   'detail': 'It is (max-mean)/sd over the ~30k nine-letter words inside ONE cell. Rebuilding the '
             'matched null for that same single cell: 150 shuffles give z=+6.67 (p=0.0066); 50 '
             'outside-family real periodic ciphers give z=+4.62 (p=0.0196). The same cell-level '
             'test on the runner-up rows falls from +9.46 to +4.15 and from +7.77 to +1.33.'},
  {'id': 'F4', 'title': 'Rebuilt search-level null: the value is inside the null band',
   'detail': '71 complete 696-cell grids. Real 0.06313. Outside-family periodic-cipher null '
             '(real sibling plaintext, n=144, random period-L key on KA): mean 0.05986, sd '
             '0.00366, max 0.06692, 3/20 replicates >= real, exact p = 0.19, z = +0.89. '
             'Shuffle null on the matched max-over-8-configs footing: exact p = 0.17. '
             'Every null replicate here searched ONE config where the real searched EIGHT, so '
             'the comparison is biased in the claim\'s favour and it still fails.'},
  {'id': 'F5', 'title': 'The claim\'s own null cannot reach significance by construction',
   'detail': 'R null replicates give a minimum achievable exact p of 1/(1+R). M-A used R=2 '
             '(p_min = 0.33) and its null run was KILLED after pk10 r0 (logs/chainA.log '
             '"Killed"); results/mk_single_null.json does not exist. M-C/M-D used R=1 '
             '(p_min = 0.50), not the "2 shuffles per target for every family" the claim states. '
             'M-E and M-B1 used R=2. Across the 10 above-ceiling comparisons, 6 fired; 4.0 are '
             'expected under H0 (sd 1.53, z = +1.31).'},
  {'id': 'F6', 'title': 'The claim\'s own derived null already kills the concat/interleave flags',
   'detail': 'results/mk_cat_derived_null.json: pk7 truncated to n=153 reaches CR 0.06803, above '
             'the real CR maximum 0.0675; pk3/pk7 at n=144 reach 0.0646-0.0657 against real '
             'maxima 0.0677-0.0680. With 4 clean derived surrogates the real values are mid-pack, '
             'not above a ceiling.'},
  {'id': 'F7', 'title': 'Multiple testing: the burden is 1e8, not 1e5',
   'detail': 'The claim counts 100,881 CELL searches. The M-A statistic is a maximum over '
             '12,521,208 word-level decrypt hypotheses per config-run, 100,169,664 per target, '
             '300,508,992 across the three targets -- for M-A alone. No analytic correction is '
             'needed because the rebuilt permutation null absorbs it directly, and it puts the '
             'real value at p ~ 0.17-0.19.'},
  {'id': 'F8', 'title': 'What a true hit looks like in this exact search',
   'detail': 'PK1 (true key PROVENANCE, a plain single dictionary word, i.e. a genuine M-A '
             'instance) run through the identical grid: 0.07052 at n=192 and 0.07012 truncated to '
             'n=144, with PROVENANCE/plain the GLOBAL argmax both times. The claim\'s own '
             'synthetics score 0.0755-0.0757 at n=144/153. The separation is clean and pk9\'s '
             '0.06313 is on the wrong side of it.'},
  {'id': 'F9', 'title': 'Confound: the statistic tracks the ciphertext\'s own IoC',
   'detail': 'Across 68 null replicates the grid maximum regresses on the ciphertext IoC with '
             'slope +0.174 (r = 0.16, residual sd 0.00282). pk9 has the highest raw IoC of the '
             'three targets (0.04448, z=+3.2). Its residual is +1.78 sd -- ordinary.'}],
 'grading': {
  'claimed_hit': 'REFUTED (Tier 3 evidence at best: a screen maximum, not a detection)',
  'family_negative': 'Tier 3 SCREEN -- FAMILY OPEN. The specific constructions and word lists are '
                     'screened, but with R=1..2 null replicates no exhaustion claim is supported, '
                     'and by the claim\'s own honest admission the depth-3 solver is unvalidated '
                     'at n=144/153 and provably degenerate for L < lcm(b,c), so the depth-3 '
                     'negative does not cover pk8/pk9 at all.'},
 'artifacts': ['results/xmk_repro.json', 'results/xmk_cell.json', 'results/xmk_degeneracy.json',
               'results/xmk_multipletesting.json', 'results/xmk_null2.json',
               'results/xmk_verdict.json', 'results/xmk_final.json'],
 'scripts': ['xmk_core.py', 'xmk_repro.py', 'xmk_cell.py', 'xmk_degen.py', 'xmk_mt.py',
             'xmk_null.py', 'xmk_null2.py', 'xmk_verdict.py', 'xmk_final.py'],
 'detail': {'reproduction': R('results/xmk_repro.json'),
            'cell_level_nulls': R('results/xmk_cell.json'),
            'degeneracy': R('results/xmk_degeneracy.json'),
            'multiple_testing': R('results/xmk_multipletesting.json'),
            'search_level_null': R('results/xmk_verdict.json')['rebuilt_search_level_matched_null'],
            'final': R('results/xmk_final.json')}}
json.dump(out, open('results/xmk_manufactured_keys_verification.json', 'w'), indent=1)
print('wrote results/xmk_manufactured_keys_verification.json')
print(json.dumps({k: v for k, v in out.items() if k != 'detail'}, indent=1)[:1500])
