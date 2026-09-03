"""Final adversarial verdict assembly for the Gromark 'above ceiling' claim (pk9, L=7, mod 10,
aca, KA, sign -1, primer 2546754, IoC 0.063714)."""
import json, math, numpy as np

nl  = json.load(open('results/mtv_null.json'))
n2  = json.load(open('results/mtv_null2.json'))['rows']
ap  = json.load(open('results/mtv_autopsy.json'))
pm  = json.load(open('results/mtv_perm.json'))
ct  = json.load(open('results/mtv_count.json'))
rp  = json.load(open('results/mtv_repro.json'))
REAL = 0.063714

# --- per-cell matched null (40 fresh seeds, identical 10^7 aca/KA/-1 enumeration)
b = np.array([r['best'] for r in n2])
mu, sd = b.mean(), b.std(ddof=1)
z_cell = (REAL-mu)/sd
# Gumbel fit (best-of-search is an extreme-value statistic, not a normal one)
scale = sd*math.sqrt(6)/math.pi; loc = mu - 0.5772*scale
p_cell = 1-math.exp(-math.exp(-(REAL-loc)/scale))

# --- search-wide null: max over the same 16 cells (4 rec x 2 alpha x 2 sign) per shuffled copy
bos = nl['best_of_search']
seeds = nl['seeds']
permax = []
for s in seeds:
    vals = [bos[rec]['s%d.%s.%s'%(s,a,g)] for rec in bos for a in ('KA','AZ') for g in ('m','p')]
    permax.append(max(vals))
permax = np.array(permax)
z_search = (REAL-permax.mean())/permax.std(ddof=1)
p_search = float((permax>=REAL).sum()+1)/(len(permax)+1)

# per-cell nulls for each of the 16 configs, from the same 40 copies
percell = {}
for rec in bos:
    for a in ('KA','AZ'):
        for g in ('m','p'):
            percell['%s.%s.%s'%(rec,a,g)] = [bos[rec]['s%d.%s.%s'%(s,a,g)] for s in seeds]

out = {
 'family':'Gromark / lagged-recurrence keystreams (frontier item 4) -- ADVERSARIAL VERIFICATION, multiple-testing lens',
 'claim_under_test':{'cell':'pk9.real.KA.m','L':7,'mod':10,'rec':'aca','alphabet':'KA','sign':-1,
   'primer':[2,5,4,6,7,5,4],'claimed_ioc':0.063714,'claimed_z':11.98,
   'claimed_pooled_null_max':0.06284,'claimed_above_ceiling':True},
 'verdict':'REFUTED',
 'reproduction':{
   'independent_kernel':'mtv_kern.py (numpy, written from the model description; not transcribed from gk_kernel.c)',
   'claimed_score_reproduced':rp['pk9.real.KA.m.aca']['best'][0],
   'exact':rp['pk9.real.KA.m.aca']['best'][0]==0.063714,
   'rank_in_full_10^7_enumeration':1,
   'runner_up':rp['pk9.real.KA.m.aca']['best'][1],
   'per_primer_mean_sd':[rp['pk9.real.KA.m.aca']['mean'],rp['pk9.real.KA.m.aca']['sd']],
   'other_cells_reproduced_exactly':{k:rp[k]['best'] for k in
       ('pk9.real.KA.p','pk9.real.AZ.m','pk9.nul1.KA.m','pk9.nul2.KA.p')},
   'roundtrip':'NOT POSSIBLE - the configuration yields no plaintext to re-encrypt',
   'key_shorter_than_plaintext':'yes in principle (7 digits vs 144 letters) but vacuous: no plaintext is produced'},
 'solver_power_positive_control':{
   'own_kernel_synthetic_n144_formA':rp['positive_control'],
   'with_width9_columnar_underneath':rp['positive_control_columnar'],
   'true_primer_score':0.070124,
   'true_primer_in_matched_null_sd_units':round((0.070124-mu)/sd,2),
   'claimed_hit_in_matched_null_sd_units':round(z_cell,2),
   'note':'a real primer lands ~7 null-sd above the null mean; the claimed hit sits at ~3.4'},
 'statistical':{
   'defect_in_claimed_z':'numerator is a MAXIMUM over 10^7 enumerated primers; denominator is the sd of a SINGLE per-primer draw (kernel mean/sd fields). (0.063714-0.039639)/0.002032 = 11.85. Max-vs-single-draw: the same mismatch as the Hill z=+5.78 and affine z=+4.91 false leads.',
   'rebuilt_matched_null':{'seeds':'900001-900040 (verifier-chosen, independent of the claim 1001/2002)',
     'draws':len(b),'identical_search':'same full 10^7 primer enumeration, rec=aca, alphabet KA, sign -1, n=144, letter-shuffled pk9 (multiset preserved)',
     'best_of_search_mean':round(float(mu),6),'best_of_search_sd':round(float(sd),6),
     'best_of_search_min':round(float(b.min()),6),'best_of_search_max':round(float(b.max()),6),
     'n_null_ge_real':int((b>=REAL).sum())},
   'recomputed_z_percell':round(float(z_cell),2),
   'gumbel_p_percell':round(p_cell,4),
   'empirical_p_percell':round((int((b>=REAL).sum())+1)/(len(b)+1),4)},
 'multiple_testing':{
   'cells_evaluated_family':ct['real_cells'],'null_cells_family':ct['null_cells'],
   'trial_decryptions_real_cells':ct['trial_decryptions_real'],
   'comparable_cells_same_search':16,
   'note_on_ceiling':'EVERY pool in this sweep carries exactly 2 matched nulls per real cell (1 at L=8). P(real best-of-search > max of its 2 nulls) = 1/3 under H0 (1/2 at L=8). "Above ceiling" is therefore a coin flip, not a threshold.',
   'exact_copy_label_permutation_test':pm,
   'rebuilt_search_wide_null':{'statistic':'max over the SAME 16 cells (4 recurrences x 2 alphabets x 2 signs) per shuffled copy',
     'draws':len(permax),'mean':round(float(permax.mean()),6),'sd':round(float(permax.std(ddof=1)),6),
     'min':round(float(permax.min()),6),'max':round(float(permax.max()),6),
     'n_null_ge_real':int((permax>=REAL).sum()),
     'expected_max_under_null':round(float(permax.mean()),6),
     'z_after_correction':round(float(z_search),2),'p_after_correction':round(p_search,3)},
   'expected_exceedances_at_percell_p_over_2032_cells':round(ct['real_cells']*p_cell,1),
   'survives_correction':False},
 'decrypt_autopsy':{
   'requirement':'a correct primer leaves MIX(P): a monoalphabetic image of the (possibly transposed) plaintext',
   'residual_hillclimb_q':ap['claimed_hit']['hillclimb_q'],
   'matched_null_40_winners':{'mean':round(float(np.mean([r['q'] for r in n2])),4),
     'sd':round(float(np.std([r['q'] for r in n2],ddof=1)),4),
     'max':round(float(np.max([r['q'] for r in n2])),4),
     'n_beating_real':int(sum(r['q']>=ap['claimed_hit']['hillclimb_q'] for r in n2))},
   'positive_control_true_primer_residual_q':ap['positive_control_true_primer']['hillclimb_q'],
   'english_monoalphabetic_reference':-4.25,
   'sorted_profile_chi2':{'real':ap['claimed_hit']['profile_chi2'],
     'null_mean':round(float(np.mean([r['chi2'] for r in n2])),4),
     'null_min':round(float(np.min([r['chi2'] for r in n2])),4),
     'n_null_more_english_than_real':int(sum(r['chi2']<=ap['claimed_hit']['profile_chi2'] for r in n2)),
     'note':'2 of 40 matched nulls have a MORE English-like sorted profile than the hit'},
   'reads_as_english_or_italian':False,
   'best_decrypt_head':ap['claimed_hit']['decrypt_head']},
 'executed_by_verifier':{
   'full_10^7_enumerations':7+40*16+40,
   'primers_enumerated':(7+40*16+40)*10**7,
   'exact_permutations_evaluated':43046721+6561+531441+729+3,
   'monoalphabetic_hillclimbs':17+40,
   'wall_sec_repro':rp['wall_sec'],'wall_sec_null_16cell':nl['wall_sec'],
   'cells_recounted_from_artifacts':{'real':ct['real_cells'],'null':ct['null_cells']}},
 'tier':{'claimed_hit':'Tier 3 - noise; not above any correctly matched ceiling',
   'family_negative_for_mod10_digit_primers_L7_L8':'Tier 2 UPHELD (exhaustive enumeration with a demonstrated positive control at the same length)',
   'open_corners':'mod-26 26^7/26^8 unenumerated; mix-after-shift at n=144/153; transposition ON TOP of the Gromark -- all Tier 3'},
 'artifacts':['mtv_kern.py','mtv_repro.py','mtv_null.py','mtv_null2.py','mtv_perm.py',
   'mtv_autopsy.py','mtv_count.py','mtv_chi2corr.py','mtv_final.py',
   'results/mtv_repro.json','results/mtv_null.json','results/mtv_null2.json',
   'results/mtv_perm.json','results/mtv_autopsy.json','results/mtv_count.json',
   'results/mtv_chi2corr.json','results/mtv_verdict.json'],
}
json.dump(out, open('results/mtv_verdict.json','w'), indent=1)
print(json.dumps({k:out[k] for k in ('verdict','statistical','multiple_testing','decrypt_autopsy')}, indent=1)[:6000])
print('\nper-cell null summary of all 16 configs (40 fresh shuffles each):')
for k,v in sorted(percell.items()):
    v=np.array(v); print('  %-14s null mean=%.6f sd=%.6f max=%.6f'%(k,v.mean(),v.std(ddof=1),v.max()))
print('\nsearch-wide max-over-16 null: mean=%.6f sd=%.6f min=%.6f max=%.6f ; REAL=%.6f  z=%.2f  p=%.3f'
      %(permax.mean(),permax.std(ddof=1),permax.min(),permax.max(),REAL,z_search,p_search))
