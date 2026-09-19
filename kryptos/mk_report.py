"""Consolidate every manufactured-key sweep into results/manufactured_keys.json."""
import json, os, sys, collections; sys.path.insert(0,'.')
import numpy as np
from lib import KA, AZ, CT, ka_to_az, qscore, ioc
import mk_lib as M
ALPH = {'KA': KA, 'AZ': AZ}
def L(p): return json.load(open(p)) if os.path.exists(p) else None
def logmax(path):
    """per-(target,rep,config) maxima straight out of a sweep log -- nothing is dropped."""
    d = collections.defaultdict(list)
    if not os.path.exists(path): return {}
    for line in open(path):
        if 'best joint=' in line:
            p = line.split(); t = p[0]; r = p[1]; cfg = p[2].rstrip(':')
            v = float(line.split('best joint=')[1].split()[0]); d[t].append(v)
        elif ' best=' in line and 'kind' not in line:
            p = line.split(); t = p[0]
            v = float(line.split(' best=')[1].split()[0]); d[t+'|'+p[4]].append(v)
    return {k: {'n_runs': len(v), 'max': max(v), 'mean': round(float(np.mean(v)),5)} for k,v in d.items()}

def singlelog(path):
    d = collections.defaultdict(list)
    if not os.path.exists(path): return {}
    for line in open(path):
        if line.startswith(('pk8','pk9','pk10')) and ' max=' in line:
            d[line.split()[0]].append(float(line.split('max=')[1]))
    return {k: {'n_config_runs': len(v), 'max': max(v), 'mean': round(float(np.mean(v)),5)}
            for k, v in d.items()}

def decrypt_two(t, ta, ka, md, a, b, Lk, wA, wB):
    ct = CT[t]; C = M.to_idx(ct, ALPH[ta]); n = len(C)
    ki = {c:i for i,c in enumerate(ALPH[ka])}
    S = (np.array([ki[c] for c in wA])[M.map_mod(n,Lk,a)] +
         np.array([ki[c] for c in wB])[M.map_mod(n,Lk,b)]) % 26
    R = (C - S) % 26 if md=='sub' else ((C + S) % 26 if md=='add' else (S - C) % 26)
    pt = ''.join(ALPH[ta][int(v)] for v in R)
    az = pt if ta=='AZ' else ka_to_az(pt)
    cnt = collections.Counter(pt)
    return {'plaintext': pt, 'ioc': round(ioc(np.array(R)),5), 'quadgram_per_letter': round(qscore(az),3),
            'top3_letters': cnt.most_common(3)}

out = {'family': 'manufactured long keys beyond the plain two-word product', 'parts': {}}

# ---------- M-B grid 1 : outer repeat length L = k*len(W1), lcm(a,b) does NOT divide L ----------
real = L('results/mk_two_real.json'); null = L('results/mk_two_null.json'); n6 = L('results/mk_two_pk8_null6.json')
if real:
    d = {'construction': 'S[i] = W1[i%a] + W2[((i%L))%b], L=k*a, lcm(a,b) does not divide L',
         'grid': 'a,b in 3..11 ordered, k=1..5, L<=55; 4 alphabet/mode configs; K=150 joint confirm',
         'executed_cell_searches_real': real['executed'], 'wall_real_sec': real['wall'],
         'real_max_joint_ioc_by_target': logmax('logs/mk_two_real.log'),
         'null_max_joint_ioc_by_target': logmax('logs/mk_two_null.log'),
         'null_shuffles_per_target': 2}
    if null: d['executed_cell_searches_null'] = null['executed']; d['wall_null_sec'] = null['wall']
    if n6:
        d['pk8_focused_null_6_shuffles'] = logmax('logs/mk_two_pk8_null6.log')
        d['executed_cell_searches_pk8_null6'] = n6['executed']
    d['top_real_rows'] = real['rows'][:6]
    d['autopsy_best_pk8'] = decrypt_two('pk8','KA','AZ','sub',7,8,28,'BENAIAH','BLOODING')
    d['autopsy_best_pk9'] = decrypt_two('pk9','AZ','AZ','sub',7,6,14,'CARALHO','CECCHI')
    out['parts']['MB1_two_word_outer_repeat'] = d

# ---------- M-B grid 2 : L not a multiple of a either (truncation cutting both words) ----------
real = L('results/mk_two2_real.json'); null = L('results/mk_two2_null.json')
if real:
    d = {'construction': 'S[i] = W1[(i%L)%a] + W2[(i%L)%b], L not a multiple of a nor of lcm(a,b)',
         'grid': 'a<b in 3..9, L in {round lengths, a+b, lcm+-1, lcm+-2, 2a+b, a+2b} <=55; 2 configs',
         'executed_cell_searches_real': real['executed'], 'wall_real_sec': real['wall'],
         'real_max_joint_ioc_by_target': logmax('logs/mk_two2_real.log'),
         'null_max_joint_ioc_by_target': logmax('logs/mk_two2_null.log'),
         'top_real_rows': real['rows'][:5]}
    if null: d['executed_cell_searches_null'] = null['executed']; d['wall_null_sec'] = null['wall']
    out['parts']['MB2_two_word_truncated'] = d

# ---------- M-A single word ----------
real = L('results/mk_single_real.json'); null = L('results/mk_single_null.json')
if real:
    d = {'construction': 'one dictionary word -> whole keystream; score = IoC of the FULL decrypt',
         'variants': 'plain / self2W=q3enc(W,W) / revsum=W+rev(W) / catrev=W||rev(W) / prog=W[i%a]+W[(i//a)%a]'
                     ' / progrev / KArun / KArunrev / AZrun / trunc L / selftrunc L / revtrunc L',
         'executed_word_list_searches_real': real['executed_word_evaluations'],
         'wall_real_sec': real['wall'], 'by_construction': {}}
    if null:
        d['executed_word_list_searches_null'] = null['executed_word_evaluations']
        d['wall_null_sec'] = null['wall']; d['null_shuffles_per_target'] = null['nshuffle']
    d['real_max_ioc_by_target_from_log'] = singlelog('logs/mk_single_real.log')
    d['null_max_ioc_by_target_from_log'] = singlelog('logs/mk_single_null.log')
    for fam, v in sorted(real['families'].items(), key=lambda x: -x[1]['max_ioc']):
        e = {'best_real_ioc': v['max_ioc'], 'best_real': v['best']}
        if null and fam in null['families']:
            e['null_max_ioc'] = null['families'][fam]['max_ioc']
            e['above_matched_ceiling'] = v['max_ioc'] > null['families'][fam]['max_ioc']
        d['by_construction'][fam] = e
    out['parts']['MA_single_word'] = d

# ---------- M-C / M-D concat + interleave ----------
real = L('results/mk_cat_real.json'); null = L('results/mk_cat_null.json')
if real:
    d = {'construction': 'C: key=W1||W2 period a+b ; CR: key=W1||reverse(W2) ; D: interleave(W1,W2)',
         'grid': 'a,b in 3..12 all ordered pairs, 4 configs, K=200 joint confirm',
         'executed_real': real['executed'], 'wall_real_sec': real['wall'],
         'max_by_kind_real': {k: (v['max_joint'] if v else None) for k,v in real['max_by_kind'].items()},
         'top_real': real['top'][:6]}
    if null:
        d['executed_null'] = null['executed']; d['wall_null_sec'] = null['wall']
        d['max_by_kind_null'] = {k: (v['max_joint'] if v else None) for k,v in null['max_by_kind'].items()}
        d['above_matched_ceiling'] = {k: (d['max_by_kind_real'][k] or 0) > (d['max_by_kind_null'][k] or 9)
                                      for k in d['max_by_kind_real']}
    out['parts']['MCD_concat_interleave'] = d

# ---------- M-E depth 3 ----------
real = L('results/mk_d3_real.json'); null = L('results/mk_d3_null.json')
if real:
    d = {'construction': 'S[i] = W1[(i%L)%a] + W2[(i%L)%b] + W3[(i%L)%c], a,b,c in 3..5',
         'cells': real['cells'], 'executed_real': real['executed'], 'wall_real_sec': real['wall'],
         'max_decoupled_z_real': real['max_zmax'], 'max_joint_ioc_real': real.get('max_joint'),
         'top_real': real['top'][:5], 'joint_top_real': real.get('joint_top', [])[:5]}
    if null:
        d['executed_null'] = null['executed']; d['wall_null_sec'] = null['wall']
        d['max_decoupled_z_null'] = null['max_zmax']; d['max_joint_ioc_null'] = null.get('max_joint')
        d['above_matched_ceiling_z'] = real['max_zmax'] > null['max_zmax']
        if real.get('max_joint') and null.get('max_joint'):
            d['above_matched_ceiling_joint'] = real['max_joint'] > null['max_joint']
    out['parts']['ME_depth3'] = d

# ---------- derived (real-sibling-ciphertext) null + degenerate-decrypt autopsy ----------
dn = L('results/mk_cat_derived_null.json')
if dn:
    out['derived_null_real_sibling_ciphertexts'] = {
      'what': 'the IDENTICAL concat/interleave search run on real Kryptos-family ciphertexts '
              '(PK3 = period-40 two-word product key, PK7 = Hill 3x3, PK6 = period-6 PORTAL) '
              'truncated to n=144/153, and on a 504-letter real-ciphertext surrogate. These keep '
              'the positional letter clustering that a letter-shuffle destroys.',
      'caveat': 'PK6 is CONTAMINATED: its true key PORTAL has period 6, which the concat family '
                'can represent as a=3,b=3, so its high maxima are a partial true fit, not a null. '
                'PK3 and PK7 are clean. The n=504 surrogate is a single concatenated string, so '
                'its 8 runs are 8 alphabet/mode configs of ONE surrogate, not 8 surrogates.',
      'per_surrogate_and_pooled_maxima': dn}
out['degeneracy_note'] = (
 'Every search maximum reported here is a DEGENERATE decrypt: one letter takes 19-21% of the '
 'text (English maximum is ~13% for E) and the quadgram score is -7.9..-8.8 per letter '
 '(random = -8.23, English = -4.25).  Peel-and-IoC maxima on a REAL ciphertext beat maxima on a '
 'letter-SHUFFLED one because a real periodic cipher leaves positional letter clustering that a '
 'shuffle destroys; the shuffle null therefore under-estimates this statistic ceiling.  The '
 'decisive benchmark is the positive control: a genuine instance of each manufacture scores '
 'IoC 0.0755-0.0757 at n=144/153 and 0.0686 at n=504, far above every observed real maximum.')
out['positive_controls'] = {'suite1': L('results/mk_positive_controls.json'),
                            'concat_interleave_depth3': L('results/mk_positive_controls_2.json'),
                            'depth3_valid': L('results/mk_d3_positive_control.json')}
json.dump(out, open('results/manufactured_keys.json','w'), indent=1)
print(json.dumps({k: {kk: vv for kk, vv in v.items() if 'top' not in kk and 'autopsy' not in kk
                      and kk != 'by_construction'} for k, v in out['parts'].items()}, indent=1))
print('WROTE results/manufactured_keys.json')
