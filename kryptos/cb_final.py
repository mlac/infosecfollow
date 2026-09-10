"""Assemble the crib-attack family into results/crib_attacks.json."""
import json, glob, os, numpy as np
R = {}
def L(p):
    try: return json.load(open(p))
    except Exception: return None
main_r, main_n = L('results/cb_main_real.json'), L('results/cb_main_null6.json')
col_r  = L('results/cb_col_real.json')
col_n8 = L('results/cb_col_null_pk8.json'); col_n9 = L('results/cb_col_null.json')
pair_r, pair_n = L('results/cb_pair_real.json'), L('results/cb_pair_null.json')
der_r, der_n = L('results/cb_main_derived.json'), L('results/cb_derived_null.json')
ev = L('results/cb_derived_events.json')
pc = L('results/cb_positive_controls.json'); pcp = L('results/cb_pair_pc.json')
aut = L('results/cb_autopsy_linear.json')

def stat(d):
    return dict(rows=d['rows'], periodic=len(d['periodic']), affine=len(d['affine']),
                fib=len(d['fib']), linear=len(d['linear']), w1=d['n_w1'], w2=d['n_w2'],
                seg=d['n_seg'], sibling=len(d['sibling']), engmax=d['eng_best'][0])
KEYS = ['periodic','affine','fib','linear','w1','w2','seg','sibling','engmax']
real = {t: stat(v) for t, v in main_r['per_text'].items()}
nulls = {}
for k, v in main_n['per_text'].items(): nulls.setdefault(k.split('_shuf')[0], []).append(stat(v))
R['battery'] = {'cribs': main_r['n_cribs'], 'structures': main_r['n_structures'],
    'per_target': {t: {'real': real[t],
        'null_mean': {k: float(np.mean([n[k] for n in nulls[t]])) for k in KEYS},
        'null_max':  {k: float(max(n[k] for n in nulls[t])) for k in KEYS},
        'n_matched_shuffles': len(nulls[t]),
        'above_null_max': {k: bool(real[t][k] > max(n[k] for n in nulls[t])) for k in KEYS}}
        for t in real},
    'totals_real': {'derivations': sum(real[t]['rows'] for t in real),
        'linear_tests': sum(main_r['per_text'][t]['lin_tests'] for t in real),
        'word_tests': sum(main_r['per_text'][t]['word_tests'] for t in real),
        'expected_false_positives_linear': sum(main_r['per_text'][t]['lin_efp'] for t in real)},
    'wall_sec_real': main_r['wall_sec'], 'wall_sec_null': main_n['wall_sec']}
R['columnar'] = {'cribs': col_r['n_cribs'], 'periods': col_r['periods'], 'min_dof': col_r['min_dof'],
    'real': {t: {'widths': v['widths'], 'solve_calls': v['n_solve_calls'],
                 'slot_orders_covered': v['n_slot_orders_covered'], 'dfs_nodes': v['nodes'],
                 'hits': len(v['hits']), 'running_key_hits': len(v['run_hits']),
                 'powered_percolumn_calls': v['powered_calls'], 'eng_best': v['eng_best'][0]}
             for t, v in col_r['per_text'].items()},
    'matched_null': {**({t: {'hits': len(v['hits']), 'run_hits': len(v['run_hits']),
                             'eng_best': v['eng_best'][0]} for t, v in col_n8['per_text'].items()}
                        if col_n8 else {}),
                     **({t: {'hits': len(v['hits']), 'run_hits': len(v['run_hits']),
                             'eng_best': v['eng_best'][0]} for t, v in col_n9['per_text'].items()}
                        if col_n9 else {})},
    'dfs_node_cap': 200000, 'max_nodes_observed_in_33880_call_sample': 75973, 'capped_calls': 0,
    'wall_sec': col_r['wall_sec']}
R['cross_target_keyfree'] = {'M': pair_r['M'], 'cribs': pair_r['n_cribs'],
    'real_tests': pair_r['per_run']['real']['n_tests'], 'real_hits': len(pair_r['per_run']['real']['hits']),
    'null_runs': len(pair_n['per_run']), 'null_hits': [len(v['hits']) for v in pair_n['per_run'].values()],
    'null_tests_each': [v['n_tests'] for v in pair_n['per_run'].values()]}
R['derived_coupling'] = {'n_texts': len(der_r['per_text']),
    'real': {t: {'w1': v['n_w1'], 'w2': v['n_w2'], 'seg': v['n_seg'],
                 'sibling': len(v['sibling']), 'periodic': len(v['periodic']),
                 'engmax': v['eng_best'][0]} for t, v in der_r['per_text'].items()},
    'null': der_n['per_run'] if der_n else None, 'events_test': ev}
R['positive_controls'] = pc
R['positive_control_cross_target'] = pcp
R['autopsy_linear_pass'] = aut
json.dump(R, open('results/crib_attacks.json', 'w'), indent=1, default=str)
print('wrote results/crib_attacks.json')
for t in R['battery']['per_target']:
    print(t, 'above_null_max:', {k: v for k, v in R['battery']['per_target'][t]['above_null_max'].items() if v})
print('totals', R['battery']['totals_real'])
print('columnar real', {t: (v['solve_calls'], v['slot_orders_covered'], v['hits'])
                        for t, v in R['columnar']['real'].items()})
print('columnar null', R['columnar']['matched_null'])
