"""Adversarial verdict assembly for the manufactured-key concat/interleave claimed hit."""
import sys,json,glob; sys.path.insert(0,'.')
import numpy as np
CLAIM=0.06799
out={}
# --- family's own artifacts, re-read ---
real=json.load(open('results/mk_cat_real.json')); null=json.load(open('results/mk_cat_null.json'))
def stratify(d):
    top=d['top']
    return {'global_max':top[0]['joint'],'global_row':{k:top[0][k] for k in ('t','cfg','kind','a','b','wA','wB')},
            'by_kind':{k:max(r['joint'] for r in top if r['kind']==k) for k in ('C','CR','D')}}
out['family_artifacts']={'real':stratify(real),'shuffle_null_1draw':stratify(null),
  'real_executed_cells':real['executed'],'null_executed_cells':null['executed'],
  'note':'family flagged above_matched_ceiling by comparing PER-KIND maxima; the search selects over kinds too'}
# --- my rebuilt nulls ---
for mode in ('relabel','shuffle'):
    try: d=json.load(open(f'results/qk_null_{mode}.json'))
    except FileNotFoundError: continue
    runs=d['runs']; draws=sorted(set(r['draw'] for r in runs))
    dm=[max(r['joint'] for r in runs if r['draw']==q) for q in draws]
    allr=[r['joint'] for r in runs]
    dm=np.array(dm); allr=np.array(allr)
    exceed=int((dm>=CLAIM).sum())
    out[f'my_null_{mode}']={
      'draws':len(dm),'runs_per_draw':len(runs)//max(len(dm),1),'cells':d['cells'],'wall_sec':d['wall'],
      'draw_max_values':[round(float(x),5) for x in dm],
      'draw_max_mean':round(float(dm.mean()),5),'draw_max_sd':round(float(dm.std(ddof=1)),5) if len(dm)>1 else None,
      'draw_max_max':round(float(dm.max()),5),
      'run_max_mean':round(float(allr.mean()),5),'run_max_sd':round(float(allr.std(ddof=1)),5),
      'z_of_claim_vs_draw_max':round(float((CLAIM-dm.mean())/dm.std(ddof=1)),3) if len(dm)>1 else None,
      'z_of_claim_vs_run_max':round(float((CLAIM-allr.mean())/allr.std(ddof=1)),3),
      'draws_at_or_above_claim':exceed,
      'empirical_p':round((exceed+1)/(len(dm)+1),4),
      'runs_at_or_above_claim':int((allr>=CLAIM).sum()),'n_runs':len(allr)}
# --- derived null (family artifact) restricted to CLEAN surrogates ---
vals=[]
for line in open('logs/mk_dnull.log'):
    if line.startswith(('pk3 n=144','pk3 n=153','pk7 n=144','pk7 n=153')):
        vals.append(float(line.split(':')[1].split('(')[0]))
v=np.array(vals)
out['derived_null_clean_pk3_pk7']={'runs':len(v),'mean':round(float(v.mean()),5),'sd':round(float(v.std(ddof=1)),5),
  'max':round(float(v.max()),5),'runs_at_or_above_claim':int((v>=CLAIM).sum()),
  'z_of_claim':round(float((CLAIM-v.mean())/v.std(ddof=1)),3),
  'note':'PK3 (period-40 two-word product) and PK7 (Hill 3x3) truncated to n=144/153: real ciphertexts, keys known and outside this family. PK6 excluded as contaminated (PORTAL period 6 == concat a=3,b=3).'}
# --- multiple testing ---
NW={3:11707,4:26126,5:38208,6:45651,7:44726,8:38356,9:29973,10:21570,11:13649,12:8170}
tot=sum(NW.values())
dec=36*sum(NW[a]+NW[b] for a in NW for b in NW)   # 3 targets x 4 cfgs x 3 kinds x 100 cells
joint=3600*200*200
out['multiple_testing']={'cells_executed':3600,'decoupled_word_scorings':dec,
  'joint_pair_IoC_evaluations':joint,'run_maxima_selected_over':36,
  'pk9_only_run_maxima':12,
  'reported_statistic':'max over ALL of the above',
  'my_null_covers':'pk9 only, 12 run maxima per draw = 1/3 of the real search, so the null is CONSERVATIVE (under-powered) by 3x'}
json.dump(out,open('results/qk_manufactured_keys_verify.json','w'),indent=1)
print(json.dumps(out,indent=1))
