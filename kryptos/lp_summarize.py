"""Aggregate scorer (a) + power + scorer (b) into results/long_periods.json."""
import json, sys, numpy as np, os
sys.path.insert(0,'.')

A = json.load(open('results/lp_ioc_raw.json'))
P = json.load(open('results/lp_power_raw.json'))
H = json.load(open('results/lp_hill_raw.json')) if os.path.exists('results/lp_hill_raw.json') else {}
G = json.load(open('results/lp_prof_raw.json'))

out = {'family': 'long periods 25-72 on PK8/PK9/PK10', 'periods': [25, 72]}

# ---- scorer (a)
sa = {'statistic': 'mean IoC of residue classes mod p (transposition-invariant)',
      'null': 'identical statistic on 2000 letter-shuffled copies of the same ciphertext, per period',
      'alphabet_note': 'IoC counts raw-letter coincidences; KA<->A-Z is a bijection on letters, '
                       'so this statistic is provably IDENTICAL for both text alphabets. '
                       'One evaluation covers both. It is also invariant to ANY per-class '
                       'monoalphabetic substitution, so it covers Vigenere/Beaufort/variant/'
                       'Quagmire I-IV/arbitrary keyed or mixed alphabets at once.',
      'controls': {}, 'targets': {}, 'power': {}}
for k in ['pk3', 'pk4']:
    f = A[k]['family']
    best = max(A[k]['rows'], key=lambda r: r['z'])
    sa['controls'][k] = dict(true_period=40 if k == 'pk3' else 45,
                             recovered_period=f['obs_argmax'], rank1=True,
                             z=round(f['obs_maxz'], 2), familywise_p=f['fam_p'],
                             obs=round(best['obs_mean'], 4), null_mean=round(best['null_mean'], 4),
                             null_max=round(best['null_max'], 4),
                             note='PK4 has a columnar transposition underneath and is still found')
for k in ['pk8', 'pk9', 'pk10']:
    f = A[k]['family']
    rows = sorted(A[k]['rows'], key=lambda r: -r['z'])[:3]
    sa['targets'][k] = dict(n=A[k]['rows'][0]['n'], best_period=f['obs_argmax'],
                            best_z=round(f['obs_maxz'], 2), familywise_p=f['fam_p'],
                            null_maxz_mean=round(f['null_maxz_mean'], 2),
                            null_maxz_p95=round(f['null_maxz_p95'], 2),
                            null_maxz_max=round(f['null_maxz_max'], 2),
                            top3=[(r['p'], round(r['z'], 2), r['minclass'], r['maxclass'],
                                   round(r['obs_mean'], 4), round(r['null_max'], 4)) for r in rows],
                            any_above_per_period_null_max=any(r['above_null_max'] for r in A[k]['rows']))
for k, v in P.items():
    rs = v['rows']
    det = {}
    for tr in (False, True):
        sub = [r for r in rs if r['transposed'] == tr]
        full = [r['p'] for r in sub if r['det_rate'] >= 0.80]
        dead = [r['p'] for r in sub if r['det_rate'] < 0.10]
        det['transposed' if tr else 'plain'] = dict(
            det_ge_80_upto=max(full) if full else None,
            first_p_det_lt_10=min(dead) if dead else None,
            det_at_25=[r['det_rate'] for r in sub if r['p'] == 25][0],
            det_at_45=[r['det_rate'] for r in sub if r['p'] == 45][0],
            det_at_72=[r['det_rate'] for r in sub if r['p'] == 72][0])
    sa['power'][k] = dict(n=v['n'], ceiling95_familywise_z=round(v['ceiling95'], 2),
                          nsyn_per_cell=60, detection=det,
                          class_size_at_p25=v['n'] // 25, class_size_at_p72=v['n'] // 72)
out['scorer_a'] = sa

# ---- scorer (a2): sorted-profile max-likelihood, same invariances, strictly sharper than IoC
sa2 = {'statistic': 'per-letter sorted-class-profile log-likelihood = EXACT max over all 26! '
                    'per-class relabellings of the multinomial loglik; IoC is a quadratic proxy for it',
       'null': 'identical statistic on 2000 letter-shuffled copies, per period',
       'invariance': 'same as scorer (a): survives an unknown columnar and any keyed/mixed alphabet',
       'controls': {}, 'targets': {}}
for k in G:
    f = G[k]['family']
    rows = sorted(G[k]['rows'], key=lambda r: -r['z'])[:3]
    rec = dict(best_period=f['obs_argmax'], best_z=round(f['obs_maxz'], 2),
               familywise_p=f['fam_p'], null_maxz_mean=round(f['null_maxz_mean'], 2),
               null_maxz_p95=round(f['null_maxz_p95'], 2), null_maxz_max=round(f['null_maxz_max'], 2),
               top3=[(r['p'], round(r['z'], 2), r['npairs'], r['z_analytic_bound']) for r in rows])
    (sa2['controls'] if k in ('pk3', 'pk4') else sa2['targets'])[k] = rec
# information budget: with an unknown transposition the ONLY invariant is the class letter
# profile, so within-class pair count is the entire evidence budget for ANY such test.
sa2['information_budget'] = {
  'formula': 'z_max ~= (IoC_eng - IoC_rand)/sqrt(IoC_rand) * sqrt(Npairs(p)) = 0.1335*sqrt(Npairs)',
  'note': 'upper bound on what ANY transposition-invariant, substitution-invariant period-p '
          'test can achieve, because a period-p polyalphabetic under an unknown permutation '
          'leaves no other usable structure',
  'bounds': {k: {'p25': [r['z_analytic_bound'] for r in G[k]['rows'] if r['p'] == 25][0],
                 'p40': [r['z_analytic_bound'] for r in G[k]['rows'] if r['p'] == 40][0],
                 'p72': [r['z_analytic_bound'] for r in G[k]['rows'] if r['p'] == 72][0]}
             for k in G}}
out['scorer_a2'] = sa2

# ---- scorer (b)
if H:
    sb = {'statistic': 'best quadgram/letter from coordinate-descent hill climb on the period-p additive key',
          'restarts': H[list(H)[0]]['family']['restarts'],
          'null': 'identical hill climb, identical restart budget, on a FIXED bank of 12 '
                  'letter-shuffled copies run at every period (gives a real family-wise ceiling)',
          'limitation': 'quadgrams are NOT transposition-invariant; blind to a columnar underneath '
                        '(demonstrated on PK4). Also assumes a pure additive/shift key per position.',
          'controls': {}, 'targets': {}}
    for k, v in H.items():
        f = v['family']
        rows = sorted(v['rows'], key=lambda r: -r['z'])[:3]
        rec = dict(best_period=f['obs_argmax'], best_z=round(f['obs_maxz'], 2),
                   familywise_p=f['fam_p'], null_maxz_mean=round(f['null_maxz_mean'], 2),
                   null_maxz_max=round(f['null_maxz_max'], 2),
                   top3=[(r['p'], round(r['z'], 2), round(r['obs'], 4), round(r['null_max'], 4),
                          r['pt'][:60]) for r in rows])
        (sb['controls'] if k.startswith('pk3') else sb['targets'])[k] = rec
    out['scorer_b'] = sb

if os.path.exists('results/lp_hill_power.json'):
    out['scorer_b_power'] = dict(
        note='synthetic period-p Vigenere over a real English window at the target length, '
             'R=40 restarts, 6-shuffle matched null; recov = fraction with >90% letters correct',
        data=json.load(open('results/lp_hill_power.json')))
if os.path.exists('results/lp_hill_raw_beau.json'):
    B = json.load(open('results/lp_hill_raw_beau.json'))
    out['scorer_b_beaufort'] = dict(
        note='identical hill climb with d=(k-c) instead of d=(c-k); validated to recover a '
             'synthetic Beaufort at n=153,p=25 with 100% letter accuracy. pk3 (a genuine ADDITIVE '
             'cipher) is included as a SPECIFICITY control: the Beaufort climb does NOT find it.',
        cells={k: dict(best_period=v['family']['obs_argmax'],
                       best_z=round(v['family']['obs_maxz'], 2),
                       familywise_p=v['family']['fam_p'],
                       null_maxz_max=round(v['family']['null_maxz_max'], 2)) for k, v in B.items()})
for tag, path in [('restart_robustness_R240', 'results/lp_hill_deep.json'),
                  ('autopsy_120null', 'results/lp_autopsy.json'),
                  ('autopsy_60null_R240', 'results/lp_autopsy2.json'),
                  ('autopsy_replication_and_negative_controls', 'results/lp_autopsy3.json')]:
    if os.path.exists(path):
        out[tag] = json.load(open(path))
out['verdict'] = {
 'pk10': 'TIER 2. Scorer (a) detects a synthetic period-p polyalphabetic at n=504 with rate 1.00 '
         'at EVERY p in 25-72, with and without a random full transposition underneath, against '
         'the family-wise 95% ceiling; observed family max-z 1.92 (p=0.77). Scorer (b) recovers '
         '>90% of the plaintext of a synthetic at every p tested (z +31..+61); observed fam_p '
         '0.25/0.83. No period-25..72 polyalphabetic of any kind on PK10.',
 'pk8_pk9': 'SPLIT. TIER 2 for p in 25..~40 with an additive or Beaufort key on KA or A-Z and NO '
            'transposition underneath: the R=240 hill climb recovers synthetics at 82-100% letter '
            'accuracy there (z +7.6..+17.9) and the real texts are flat. TIER 3 for p above ~40, '
            'and TIER 3 across the whole 25-72 range if a columnar sits underneath, because both '
            'transposition-invariant scorers are provably out of information at these lengths.',
 'why_a_is_powerless_on_pk8_pk9': 'With an unknown transposition the ONLY invariant left is the '
            'within-class letter profile, so the within-class pair count is the entire evidence '
            'budget. At n=153 it is 393 pairs at p=25 (z ceiling 2.65) falling to 90 pairs at '
            'p=72 (z ceiling 1.27); at n=144, 345 down to 72 pairs (2.48 -> 1.13). Measured '
            'detection rates track this: 0.30 at p=25, under 0.10 by p=45. At n=504 the same '
            'budget is 4830 down to 1512 pairs (ceiling 9.28 -> 5.19), hence detection 1.00.',
 'flagged_and_killed': 'Seven cells beat a small (10-12 shuffle) per-period null max. All died: '
            'four at a 120-shuffle null (p=0.775/0.142/0.200/0.108); the two that survived a '
            '60-shuffle null at R=240 (pk8/KA p=72 z=+2.47, pk9/AZ p=42 z=+3.38) failed to '
            'replicate on an independent re-run (z=+0.36 p=0.35 and z=+1.71 p=0.05) and their '
            'neighbouring periods and six SOLVED-ciphertext negative controls (PK1/PK2/PK5/PK6/PK7 '
            'truncated to the same length, all with provably no period 25-72 key) span the same '
            'z range (-2.30..+1.88). The decrypts are quadgram-overfit garble at 2.1-3.4 letters '
            'per key slot. Nothing exceeded the family-wise matched null max from its own search.'}
json.dump(out, open('results/long_periods.json', 'w'), indent=1)

if os.path.exists('results/lp_globalioc.json'):
    out['cross_check_whole_text_ioc'] = dict(
        note='whole-text IoC is invariant to transposition AND to the per-class substitutions; '
             'a period-p polyalphabetic drives it to ~0.0385+0.026/p. Simulated 3000 synthetic '
             'period-p ciphertexts (English window, random full permutation, random key) per cell.',
        data=json.load(open('results/lp_globalioc.json')),
        verdict='PK9 sits 2.3-3.0 sigma ABOVE what any period 25-72 polyalphabetic produces '
                '(two-sided p 0.015-0.05) -- the wrong direction, an independent strike against '
                'a long period on PK9. PK8 and PK10 are consistent with either.')
json.dump(out, open('results/long_periods.json', 'w'), indent=1)
print(json.dumps(out, indent=1)[:6000])
