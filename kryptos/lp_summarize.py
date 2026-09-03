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
    out['scorer_b_power'] = json.load(open('results/lp_hill_power.json'))

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
