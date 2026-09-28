"""xmk_verdict: assemble the adversarial verification of the manufactured-long-key claim."""
import sys, json, os, collections; sys.path.insert(0, '.')
import numpy as np

R = lambda p: json.load(open(p))
repro = R('results/xmk_repro.json')
cell = R('results/xmk_cell.json')
mt = R('results/xmk_multipletesting.json')
deg = R('results/xmk_degeneracy.json')
n2 = R('results/xmk_null2.json')

reps = n2['replicates']
by = collections.defaultdict(list)
for r in reps:
    by[r['kind']].append(r)
real = by['REAL'][0]['grid_max']

def stats(kind):
    v = np.array([r['grid_max'] for r in by.get(kind, [])])
    if not len(v):
        return None
    return {'n_replicates': int(len(v)), 'mean': round(float(v.mean()), 5),
            'sd': round(float(v.std(ddof=1)), 5) if len(v) > 1 else None,
            'min': round(float(v.min()), 5), 'p95': round(float(np.percentile(v, 95)), 5),
            'max': round(float(v.max()), 5),
            'z_of_real': round(float((real - v.mean()) / v.std(ddof=1)), 2) if len(v) > 1 else None,
            'n_ge_real': int((v >= real).sum()),
            'exact_permutation_p': round(float((1 + (v >= real).sum()) / (1 + len(v))), 4)}

out = {
 'what_was_verified': (
   'The headline of the manufactured-long-key family: the M-A single-word sweep on PK9, '
   'max decrypt-IoC 0.06313 at KA/AZ/sub, construction revtrunc14, key METALHEAD (a=9), '
   'reported with an in-cell z of +8.1 and flagged above the matched shuffle-null ceiling '
   '(null max 0.06070 from 2 shuffles).'),
 'reproduction': {
   'headline_recomputed_ioc': repro['MA_headline']['recomputed_ioc'],
   'claimed': repro['MA_headline']['claimed_ioc'],
   'reproduces_exactly': repro['MA_headline']['recomputed_ioc'] == repro['MA_headline']['claimed_ioc'],
   'reproduced_through_an_independently_written_search': True,
   'MB1_pk8_recomputed': repro['MB1_headline_pk8']['ioc'],
   'MB1_pk9_recomputed': repro['MB1_headline_pk9']['ioc'],
   'round_trip': deg['round_trip']},
 'is_the_decrypt_language': {
   'headline': deg['headline_decrypt_pk9_METALHEAD_revtrunc14'],
   'real_sibling_plaintext_n144_reference': deg['real_sibling_plaintext_n144'],
   'verdict': 'NO. quadgram -8.07/letter (random -8.23, English -4.25); 58% of the IoC comes '
              'from a single letter occupying 19.4% of the text.'},
 'the_z_is_the_wrong_z': {
   'reported_in_cell_z': 8.1,
   'what_it_is': 'max minus mean over the ~30k dictionary words INSIDE one cell '
                 '(one construction, one config). It is a within-cell z, not a search z.',
   'rebuilt_cell_level_matched_nulls': cell['cells'],
   'note': 'Even the correctly matched single-cell z falls from +8.1 to +6.67 (150 shuffles) and '
           'to +4.62 (50 outside-family real periodic ciphers) -- and that is still a single cell '
           'out of 5568 searched per target.'},
 'rebuilt_search_level_matched_null': {
   'design': n2['design'],
   'statistic': 'max decrypt-IoC over one complete 696-cell M-A grid',
   'conservative_bias_note': (
     'The real value 0.06313 is the maximum over EIGHT alphabet/mode configs; each null replicate '
     'here is a maximum over ONE. The comparison is therefore biased IN THE CLAIM S FAVOUR.'),
   'real_pk9': real,
   'SHUFFLE_null_the_claims_own_construction': stats('S'),
   'SYNTHETIC_outside_family_periodic_ciphers': stats('N'),
   'DERIVED_null_real_sibling_ciphertexts_keys_outside_family': stats('D'),
   'positive_control_PK1_true_plain_word_key': [
     {'label': r['label'], 'grid_max': r['grid_max'], 'argmax': r['argmax']} for r in by.get('POSCTL', [])],
   'null_argmax_examples': [{'label': r['label'], 'grid_max': r['grid_max'], 'argmax': r['argmax']}
                            for r in sorted(by.get('S', []) + by.get('N', []) + by.get('D', []),
                                            key=lambda x: -x['grid_max'])[:8]]},
 'multiple_testing': mt,
 'wall_sec_of_this_verification': n2['wall'],
}
json.dump(out, open('results/xmk_verdict.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != 'multiple_testing'}, indent=1))
