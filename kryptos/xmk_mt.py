"""xmk_mt: multiple-testing and exchangeability audit of the claim's OWN artifacts.

Every 'above_matched_ceiling' flag in results/manufactured_keys.json is a comparison of
  max over the real search   vs   max over R null replicates of the identical search.
Under H0 the (1+R) replicate maxima are exchangeable, so the exact permutation p-value of
'real is the largest' is 1/(1+R).  R is read straight out of the null artifacts."""
import sys, json, math, collections; sys.path.insert(0,'.')
import numpy as np

out={'per_family':{}, 'notes':[]}
def add(name, real, nulls, R, stat):
    nulls=list(nulls)
    p=(1+sum(1 for v in nulls if v>=real))/(1+len(nulls)) if nulls else None
    out['per_family'][name]={'statistic':stat,'real_max':real,'null_replicate_maxima':nulls,
      'n_null_replicates_R':R,'above_null_max':bool(nulls and real>max(nulls)),
      'exact_permutation_p':round(p,4) if p else None,
      'MINIMUM_ACHIEVABLE_p_with_this_R':round(1.0/(1+R),4)}

# --- M-A single word.  Null log was scraped from logs/mk_single_null.log; the run was KILLED
#     (logs/chainA.log: 'Killed') so results/mk_single_null.json was never written.
def runmax(path):
    d=collections.defaultdict(list)
    for line in open(path):
        if line.startswith(('pk8','pk9','pk10')) and ' max=' in line:
            p=line.split(); d[(p[0],p[1])].append(float(line.split('max=')[1]))
    return {k:max(v) for k,v in d.items()}
R=runmax('logs/mk_single_real.log'); N=runmax('logs/mk_single_null.log')
for t in ('pk8','pk9','pk10'):
    nl=[v for (tt,r),v in N.items() if tt==t]
    add(f'MA_single_{t}', R[(t,'r0')], nl, len(nl), 'max decrypt-IoC over one full 696-cell x 8-config search')
out['notes'].append('MA null run was KILLED after pk10 r0 (logs/chainA.log: "Killed"); '
  'results/mk_single_null.json does not exist. pk8/pk9 got 2 shuffles, pk10 got 1.')

# --- M-B1 two-word outer repeat: 2 shuffles (+ focused 6-shuffle pk8 re-run)
mk=json.load(open('results/manufactured_keys.json'))
b1=mk['parts']['MB1_two_word_outer_repeat']
for t in ('pk8','pk9','pk10'):
    rm=b1['real_max_joint_ioc_by_target'][t]['max']
    nn=b1['null_max_joint_ioc_by_target'][t]
    # the artifact only stores the pooled max/mean over n_runs config-runs, not per replicate;
    # replicates = n_runs / 4 configs
    Rn=nn['n_runs']//4
    out['per_family'][f'MB1_{t}']={'statistic':'max joint IoC over the 300-cell two-word grid',
      'real_max':rm,'null_pooled_max':nn['max'],'null_pooled_mean':nn['mean'],
      'n_null_replicates_R':Rn,'above_null_max':rm>nn['max'],
      'MINIMUM_ACHIEVABLE_p_with_this_R':round(1.0/(1+Rn),4)}
out['per_family']['MB1_pk8']['focused_6shuffle_null_max']=b1['pk8_focused_null_6_shuffles']['pk8']['max']
out['per_family']['MB1_pk8']['above_focused_null_max']=b1['real_max_joint_ioc_by_target']['pk8']['max']>b1['pk8_focused_null_6_shuffles']['pk8']['max']
out['per_family']['MB1_pk8']['MIN_p_focused_R6']=round(1/7,4)

# --- M-C/M-D concat / interleave: nshuffle = 1
cd=mk['parts']['MCD_concat_interleave']
for k in ('C','CR','D'):
    add(f'MCD_{k}', cd['max_by_kind_real'][k], [cd['max_by_kind_null'][k]], 1,
        'max joint IoC over the 3600-cell concat/interleave grid')
# --- M-E depth 3: nshuffle = 2
me=mk['parts']['ME_depth3']
out['per_family']['ME_depth3_joint']={'statistic':'max joint IoC, depth-3 grid',
  'real_max':me['max_joint_ioc_real'],'null_pooled_max':me['max_joint_ioc_null'],
  'n_null_replicates_R':2,'above_null_max':me['max_joint_ioc_real']>me['max_joint_ioc_null'],
  'MINIMUM_ACHIEVABLE_p_with_this_R':round(1/3,4)}
out['per_family']['ME_depth3_z']={'statistic':'max decoupled z, depth-3 grid',
  'real_max':me['max_decoupled_z_real'],'null_pooled_max':me['max_decoupled_z_null'],
  'above_null_max':me['max_decoupled_z_real']>me['max_decoupled_z_null']}

# --- how many 'above ceiling' flags, and how many are expected by chance
flags=[('MA_pk8',out['per_family']['MA_single_pk8']['above_null_max'],2),
       ('MA_pk9',out['per_family']['MA_single_pk9']['above_null_max'],2),
       ('MA_pk10',out['per_family']['MA_single_pk10']['above_null_max'],1),
       ('MB1_pk8',out['per_family']['MB1_pk8']['above_null_max'],2),
       ('MB1_pk9',out['per_family']['MB1_pk9']['above_null_max'],2),
       ('MB1_pk10',out['per_family']['MB1_pk10']['above_null_max'],2),
       ('MCD_C',out['per_family']['MCD_C']['above_null_max'],1),
       ('MCD_CR',out['per_family']['MCD_CR']['above_null_max'],1),
       ('MCD_D',out['per_family']['MCD_D']['above_null_max'],1),
       ('ME_joint',out['per_family']['ME_depth3_joint']['above_null_max'],2)]
obs=sum(1 for _,f,_ in flags if f)
exp=sum(1.0/(1+R) for _,_,R in flags)
out['above_ceiling_flag_audit']={'flags':{n:bool(f) for n,f,_ in flags},
  'observed_flags':obs,'expected_flags_under_H0':round(exp,2),
  'comment':'Under H0 each flag fires with probability 1/(1+R). The observed count is what the '
            'null design produces by construction; no flag can reach p<1/(1+R).'}
out['hypothesis_counts']={
  'MA_word_level_decrypt_hypotheses_per_target':100169664,
  'MA_cells_per_target':5568,
  'MA_word_level_hypotheses_all_3_targets':300508992,
  'claim_executed_configs_field':100881,
  'comment':'The claim counts CELL-searches (100,881). The multiple-testing burden of the M-A '
            'statistic is the number of distinct decrypt-IoC values maximised over: 1.0e8 per '
            'target for M-A alone.'}
json.dump(out,open('results/xmk_multipletesting.json','w'),indent=1)
print(json.dumps(out,indent=1))
