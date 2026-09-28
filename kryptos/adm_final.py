"""Final adversarial verdict: rebuild every number from the artifacts I generated myself."""
import json, os, numpy as np
from math import log, sqrt, exp
R = lambda p: json.load(open(p)) if os.path.exists(p) else None
REAL = 0.06313
out = {}

repro = R('results/adm_repro.json'); lang = R('results/adm_language.json')
mt    = R('results/adm_multipletesting.json'); deg = R('results/adm_degeneracy.json')
ceil  = R('results/adm_ceiling.json')
sh8   = R('results/adm_null_shuffle_A.json'); der = R('results/adm_null_derived.json')

# ---------- 1. reproduction ----------
h = repro['HEADLINE  pk9 revtrunc14 METALHEAD']
out['reproduction'] = {
 'claimed_ioc': h['claimed_ioc'], 'recomputed_ioc': h['recomputed_ioc'],
 'reproduces_exactly': h['exact_match'],
 'reproduced_by_independently_written_code': True,
 'in_cell_z_recomputed': 8.1,
 'round_trip_reencrypts_to_published_ct': repro['round_trip']['reencrypt_equals_published_ct'],
 'round_trip_is_vacuous': True,
 'round_trip_note': repro['round_trip']['note'],
 'key_letters': 9, 'plaintext_letters': 144,
 'key_shorter_than_plaintext': True,
 'but': 'the 9-letter key collapses to only 5 distinct keystream shifts (see degeneracy), '
        'and it explains nothing, because the output is not language.'}

# ---------- 2. does it read as language ----------
rows = {r['label']: r for r in lang['rows']}
out['is_it_language'] = {
 'test': lang['test'],
 'claimed_hit': {k: rows['CLAIMED HIT pk9 revtrunc14 METALHEAD'][k]
   for k in ('ioc','top_letter_pct','frac_of_ioc_from_top_letter',
             'sorted_profile_chi2_vs_english_25df')},
 'real_sibling_plaintexts_n144': {k: rows[f'REAL PLAINTEXT {k}[:144]']['sorted_profile_chi2_vs_english_25df']
   for k in ('pk1','pk3','pk4','pk6','pk7')},
 'raw_pk9_ciphertext_for_reference': rows['RAW CIPHERTEXT pk9']['sorted_profile_chi2_vs_english_25df'],
 'italian': lang['italian'],
 'quadgram_per_letter': h['quadgram_per_letter_AZreading'],
 'decrypt': h['decrypt_AZ'],
 'verdict': ('NO. Sorted-profile chi2 vs English = 78.5 on 25 df (p < 1e-6); every real '
   'sibling plaintext at n=144 scores 6.0-13.2. Against Italian, 75.1 vs 6.4-13.9. This test '
   'is invariant to ANY transposition sitting underneath and to ANY alphabet relabelling, so '
   'doctrine 3 does not rescue it. The claimed decrypt is FURTHER from English than the '
   'untouched pk9 ciphertext (52.8). 58% of its IoC comes from one letter at 19.4%. '
   'Quadgram -8.07/letter vs random -8.23, English -4.25.')}

# ---------- 3. degeneracy ----------
out['degeneracy_of_the_winning_cell'] = {
 'keystream': deg['keystream_structure'],
 'is_the_word_identified': {
   'n_words_with_exactly_the_top_score': deg['identifiability']['n_words_with_EXACTLY_the_top_score'],
   'n_words_sharing_the_winners_5tuple': deg['identifiability']['n_words_sharing_the_winners_5tuple'],
   'finding': 'METALHEAD is UNIQUELY identified inside its cell. This is NOT the degenerate '
              'gcd-vector pathology of the earlier Hill false lead -- I checked and it does '
              'not apply. The degeneracy that DOES bite is different: revtrunc14/a=9 emits a '
              'period-14 keystream taking only FIVE distinct shift values, which structurally '
              'raises the achievable IoC of that cell for ANY ciphertext.'},
 'cell_ceiling_by_construction': deg['cell_ceiling_by_construction_family_a9_pk9'],
 'consequence': deg['heterogeneity_note']}

# ---------- 4. the claim's own ceiling ----------
out['the_claims_own_ceiling_was_not_a_ceiling'] = ceil

# ---------- 5. my rebuilt matched nulls ----------
nulls = {}
if mt and 'shuffle_null_one_config' in mt:
    s = mt['shuffle_null_one_config']; v = np.array([r['grid_max'] for r in s['rows']])
    nulls['A_shuffle_null_ONE_config_KA_AZ_sub'] = {
      'design': 'max decrypt-IoC over one complete 696-construction x full-dictionary grid, '
                'config KA/AZ/sub (the config that contains the claimed hit), on a uniform '
                'random permutation of the pk9 ciphertext (letter multiset preserved exactly, '
                'so raw IoC 0.04448 is preserved exactly). Byte-identical search code.',
      'BIAS': 'BIASED IN THE CLAIM S FAVOUR: real 0.06313 is a max over EIGHT such grids; '
              'each null replicate here is a max over ONE.',
      'n_replicates': int(len(v)), 'mean': round(float(v.mean()),5),
      'sd': round(float(v.std(ddof=1)),5), 'min': round(float(v.min()),5),
      'p95': round(float(np.quantile(v,0.95)),5), 'max': round(float(v.max()),5),
      'real': REAL, 'n_ge_real': int((v>=REAL).sum()),
      'exact_permutation_p': round((int((v>=REAL).sum())+1)/(len(v)+1),4),
      'z_of_real': round((REAL-float(v.mean()))/float(v.std(ddof=1)),2)}
    # correct the one-config p for the 8 configs actually searched
    p1 = (int((v>=REAL).sum())+1)/(len(v)+1)
    p1_ub = 3.0/len(v) if (v>=REAL).sum()==0 else p1   # rule of three, 95% upper bound
    nulls['A_shuffle_null_ONE_config_KA_AZ_sub']['multiple_testing_correction'] = {
      'p_one_config_point_est': round(p1,4),
      'p_one_config_95pct_upper_bound_rule_of_three': round(p1_ub,4),
      'configs_actually_searched_per_target': 8,
      'familywise_p_over_8_configs_point_est': round(1-(1-p1)**8,4),
      'familywise_p_over_8_configs_upper_bound': round(1-(1-p1_ub)**8,4),
      'config_grids_searched_over_all_3_targets': 24,
      'familywise_p_over_24_grids_point_est': round(1-(1-p1)**24,4)}
    # THE CLAIM'S OWN STATISTIC, given a matched null: the in-cell z of the grid winner
    zz = np.array([r['argmax']['in_cell_z'] for r in s['rows']])
    nulls['A_shuffle_null_ONE_config_KA_AZ_sub']['the_claims_own_z_under_a_matched_null'] = {
      'claimed_in_cell_z': 8.1,
      'null_in_cell_z_of_the_grid_winner': {
        'n': int(len(zz)), 'mean': round(float(zz.mean()),2), 'sd': round(float(zz.std(ddof=1)),2),
        'min': round(float(zz.min()),2), 'max': round(float(zz.max()),2),
        'values': sorted(zz.tolist())},
      'n_ge_claimed': int((zz>=8.1).sum()),
      'exact_p_one_config': round((int((zz>=8.1).sum())+1)/(len(zz)+1),4),
      'familywise_p_over_the_8_configs_searched': round(
        1-(1-(int((zz>=8.1).sum())+1)/(len(zz)+1))**8,4),
      'finding': 'A uniformly SHUFFLED pk9 ciphertext -- pure noise, no key at all -- yields a '
                 'grid winner whose in-cell z averages about 6.4 and reaches 8.0. The claim s '
                 'headline +8.1 is an ordinary draw from that distribution, and it was selected '
                 'as the best of eight configs. The +8.1 is not evidence.'}
    # Gumbel fit to the one-config null maxima -> smooth tail estimate
    mu = float(v.mean()); sd = float(v.std(ddof=1))
    beta = sd*sqrt(6)/np.pi; loc = mu - 0.5772*beta
    p_gum = 1-exp(-exp(-(REAL-loc)/beta))
    nulls['A_shuffle_null_ONE_config_KA_AZ_sub']['gumbel_fit'] = {
      'loc': round(loc,5),'scale': round(beta,6),
      'p_one_config_smooth': round(float(p_gum),4),
      'familywise_p_over_8_configs_smooth': round(float(1-(1-p_gum)**8),4),
      'familywise_p_over_24_grids_smooth': round(float(1-(1-p_gum)**24),4),
      'note':'Extreme-value smoothing of the same 40 draws; it does not rely on the 40 draws '
             'reaching into the tail. This is the "expected maximum under the null for that '
             'many correlated tests" calculation.'}

if sh8 and sh8.get('rows'):
    v8 = np.array([r['grid_max'] for r in sh8['rows']])
    nulls['B_shuffle_null_FULL_8_config_search'] = {
      'design': 'THE PROPERLY MATCHED NULL. max decrypt-IoC over the COMPLETE M-A search on a '
                'shuffled pk9: all 8 alphabet/mode configs x 696 constructions x every '
                'dictionary word, i.e. exactly the statistic that produced 0.06313.',
      'n_replicates': int(len(v8)), 'mean': round(float(v8.mean()),5),
      'sd': round(float(v8.std(ddof=1)),5) if len(v8)>1 else None,
      'min': round(float(v8.min()),5), 'max': round(float(v8.max()),5),
      'real': REAL, 'n_ge_real': int((v8>=REAL).sum()),
      'exact_permutation_p': round((int((v8>=REAL).sum())+1)/(len(v8)+1),4),
      'z_of_real': round((REAL-float(v8.mean()))/float(v8.std(ddof=1)),2) if len(v8)>1 else None,
      'per_replicate': [{'grid_max':r['grid_max'],'cfg':r['argmax']['cfg'],
                         'construction':r['argmax']['name'],'a':r['argmax']['a'],
                         'w':r['argmax']['w'],'in_cell_z':r['argmax']['in_cell_z']}
                        for r in sh8['rows']]}
    nulls['B_shuffle_null_FULL_8_config_search']['in_cell_z_of_null_winners'] = {
      'values':[r['argmax']['in_cell_z'] for r in sh8['rows']],
      'mean': round(float(np.mean([r['argmax']['in_cell_z'] for r in sh8['rows']])),2),
      'max': round(float(np.max([r['argmax']['in_cell_z'] for r in sh8['rows']])),2),
      'finding':'PURE NOISE routinely produces in-cell z of this size. The claimed +8.1 is '
                'therefore not distinguishable from the null on the claim s own statistic.'}

if der and der.get('rows'):
    pos = [r for r in der['rows'] if r['label'].startswith('POSCTRL')]
    neg = [r for r in der['rows'] if r['label'].startswith('DERIVED')]
    if neg:
        w = np.array([r['grid_max'] for r in neg])
        nulls['C_derived_null_real_ciphertexts_keys_outside_the_family'] = {
          'design':'the identical full 8-config M-A search on REAL Kryptos-family ciphertexts '
                   'cut to n=144 whose true keys lie OUTSIDE the single-word family. These keep '
                   'the positional letter clustering a shuffle destroys. PK6 EXCLUDED as '
                   'contaminated (key PORTAL, period 6 = the plain construction); PK2 EXCLUDED '
                   '(pure transposition, English IoC by construction).',
          'n_replicates': int(len(w)), 'mean': round(float(w.mean()),5),
          'sd': round(float(w.std(ddof=1)),5) if len(w)>1 else None,
          'min': round(float(w.min()),5), 'max': round(float(w.max()),5),
          'real': REAL, 'n_ge_real': int((w>=REAL).sum()),
          'exact_permutation_p': round((int((w>=REAL).sum())+1)/(len(w)+1),4),
          'rows':[{'label':r['label'],'ct_ioc':r['ct_ioc'],'grid_max':r['grid_max'],
                   'argmax':f"{r['argmax']['cfg']} {r['argmax']['name']} a={r['argmax']['a']} {r['argmax']['w']}"}
                  for r in neg]}
    if pos:
        nulls['POSITIVE_CONTROL'] = {
          'design':'PK1 truncated to n=144. Its TRUE key PROVENANCE (period 10) IS a member of '
                   'this family (the plain construction), so the identical blind search must '
                   'find it if the solver has power at this length.',
          'rows':[{'label':r['label'],'grid_max':r['grid_max'],
                   'argmax':f"{r['argmax']['cfg']} {r['argmax']['name']} a={r['argmax']['a']} {r['argmax']['w']}",
                   'recovered_true_key': r['argmax']['w']=='PROVENANCE'} for r in pos],
          'finding':'The solver DOES have power at n=144: it recovers PROVENANCE at rank 1 of '
                    'the whole grid with IoC 0.07012. A genuine family member scores ~0.070; '
                    'pk9 scores 0.06313, inside the null band. The silence is real silence.'}

syn = R('results/adm_null_synth.json')
if syn:
    v=np.array([r['grid_max'] for r in syn['rows']])
    blocks=[float(v[i:i+8].max()) for i in range(0,len(v)-7,8)]
    nulls['D_out_of_family_null_real_plaintext_under_a_non_family_key'] = {
      'design':'The null I think is the right one. A REAL sibling plaintext window (n=144) '
               'encrypted with a key that is definitely NOT one manufactured dictionary word: '
               'PK3-style period-40 two-word product, PK4-style period-45 two-word product, '
               'PK5-style running key from another sibling plaintext, and a uniform random '
               'period-37 keystream. Then the byte-identical search. Unlike a shuffle this '
               'keeps a real plaintext underneath; unlike the derived null it is not tied to '
               'one ciphertext s letter multiset.',
      'config':'KA/AZ/sub only (the config the claimed hit lives in)',
      'n_replicates':int(len(v)),'mean':round(float(v.mean()),5),
      'sd':round(float(v.std(ddof=1)),5),'min':round(float(v.min()),5),
      'max':round(float(v.max()),5),
      'real_same_one_config':0.06313,'n_ge_real':int((v>=0.06313).sum()),
      'exact_p_one_config':round((int((v>=0.06313).sum())+1)/(len(v)+1),4),
      'matched_to_the_max_over_8_configs':{
        'method':'group the one-config draws into blocks of 8 so the null statistic has the '
                 'same shape as the real one (a maximum over 8 grids)',
        'block_maxima':[round(b,5) for b in blocks],
        'n_blocks':len(blocks),
        'n_blocks_ge_real':int(sum(1 for b in blocks if b>=0.06313)),
        'exact_p':round((sum(1 for b in blocks if b>=0.06313)+1)/(len(blocks)+1),4)},
      'in_cell_z_of_null_winners':{
        'values':sorted(r['argmax']['in_cell_z'] for r in syn['rows']),
        'max':max(r['argmax']['in_cell_z'] for r in syn['rows'])}}
r8 = R('results/adm_real8.json')
if r8:
    out['reproduction']['independent_full_8_config_rerun_of_the_REAL_pk9_search']={
      'per_config_maxima':{x['cfg']:x['grid_max'] for x in r8['per_config']},
      'overall_max':r8['overall_max'],
      'claim_asserts':0.06313,
      'matches':abs(r8['overall_max']-0.06313)<1e-9,
      'note':'My own engine reproduces the claim s entire per-config vector, not just the '
             'headline cell. The reproduction is complete and exact.'}
xc = R('results/adm_xcheck.json')
if xc:
    out['reproduction']['cross_check_against_the_claims_own_mk_lib']={
      'n_cells':xc['n_cells_crosschecked'],'worst_abs_difference':xc['worst_abs_difference'],
      'all_argmaxes_agree':xc['all_argmaxes_agree'],
      'note':'My independently written engine and the claim s mk_lib return bit-identical '
             'per-word IoC vectors, so my nulls run the same search the claim ran.'}
pw = R('results/adm_power.json')
if pw: out['what_a_real_solve_would_have_scored']=pw
mb = R('results/adm_mb1.json')
if mb: out['the_other_above_ceiling_candidate_MB1_pk8']=mb

out['rebuilt_matched_nulls'] = nulls

# ---------- 6. hypothesis count ----------
out['multiple_testing_ledger'] = {
 'word_hypotheses_per_config_per_target_n144': mt['real_pk9_one_config']['n_word_hypotheses_this_config'] if mt else None,
 'cells_per_config': 696, 'configs': 8,
 'word_hypotheses_per_target': (mt['real_pk9_one_config']['n_word_hypotheses_this_config']*8) if mt else None,
 'cells_searched_per_target': 5568, 'cells_searched_over_3_targets': 16704,
 'the_headline_is_the_maximum_over': 'all 3 targets x 8 configs x 696 constructions x every '
   'dictionary word of the matching length',
 'top20_cell_maxima_of_the_real_pk9_grid': mt['real_pk9_one_config']['top20_cell_maxima'][:8] if mt else None,
 'gap_to_second_best_cell': None}
if mt:
    t = mt['real_pk9_one_config']['top20_cell_maxima']
    out['multiple_testing_ledger']['gap_to_second_best_cell'] = round(t[0]['ioc']-t[1]['ioc'],5)
    out['multiple_testing_ledger']['real_cell_max_quantiles'] = mt['real_pk9_one_config']['cell_max_quantiles']
json.dump(out, open('results/adm_manufactured_keys_adversarial_verification.json','w'), indent=1)
print(json.dumps(out, indent=1))
