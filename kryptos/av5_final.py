"""ADVERSARIAL VERIFICATION VERDICT, frontier item 5 (word-constrained dual beam, PK10)."""
import json, numpy as np, glob
rows=[]
for f in sorted(glob.glob('results/av5_null_*.json')):
    rows += json.load(open(f))
rows.sort(key=lambda r: r['shuffle'])
N=len(rows)
add =np.array([r['add']  for r in rows]); sub=np.array([r['sub'] for r in rows])
beau=np.array([r['beau'] for r in rows]); mx =np.array([r['max3'] for r in rows])
REAL={'add':-6.4826,'sub':-6.4390,'beau':-6.4241}
REAL_MAX3=max(REAL.values())
pub=np.array([x['obj'] for x in json.load(open('results/wb_dual_null_k8.json'))])

def st(a): return dict(n=int(a.size),mean=round(float(a.mean()),4),
                       sd=round(float(a.std(ddof=1)),4),max=round(float(a.max()),4),
                       min=round(float(a.min()),4))
def z(x,a): return round(float((x-a.mean())/a.std(ddof=1)),2)

out={}
out['reproduction']=json.load(open('results/av5_repro.json'))
out['published_null_mode_add_only']=st(pub)
out['rebuilt_null']={'shuffle_seeds':'default_rng(1000+s), s=0..%d (SAME seeds as the published null)'%(N-1),
                     'add':st(add),'sub':st(sub),'beau':st(beau),
                     'max_over_3_modes_per_replicate':st(mx),
                     'add_arm_reproduces_published_null':bool(
                         all(abs(rows[i]['add']-pub[rows[i]['shuffle']])<1e-9 for i in range(N) if rows[i]['shuffle']<len(pub)))}
out['the_claimed_hit']={
  'cell':'PK10, KA, key vocab len>=8, mode BEAUFORT, beam 100000, Wpt=1.0 Wkey=2.0',
  'obj':-6.4241,
  'as_published':{'null':'8 shuffles, mode ADD only','null_max':round(float(pub.max()),4),
                  'excess':round(float(-6.4241-pub.max()),4),'z':z(-6.4241,pub),
                  'above_null_max':bool(-6.4241>pub.max())},
  'mode_matched':{'null':'%d shuffles, mode BEAUFORT (identical beam)'%N,
                  'null_mean':st(beau)['mean'],'null_sd':st(beau)['sd'],'null_max':st(beau)['max'],
                  'z':z(-6.4241,beau),'above_null_max':bool(-6.4241>beau.max())},
  'mode_matched_and_multiplicity_matched':{
     'null':'%d shuffles; each replicate = MAX over the same 3 modes the real search maximised over'%N,
     'real_statistic':REAL_MAX3,'null_mean':st(mx)['mean'],'null_sd':st(mx)['sd'],
     'null_max':st(mx)['max'],'z':z(REAL_MAX3,mx),'above_null_max':bool(REAL_MAX3>mx.max()),
     'empirical_p':round(float((mx>=REAL_MAX3).sum()+1)/(N+1),4)},
}
out['per_mode_real_vs_matched_null']={m:{'real':REAL[m],'null_mean':st(a)['mean'],
    'null_sd':st(a)['sd'],'null_max':st(a)['max'],'z':z(REAL[m],a),
    'above_null_max':bool(REAL[m]>a.max())}
    for m,a in (('add',add),('sub',sub),('beau',beau))}
out['mode_effect_in_the_null']={
  'add_mean':st(add)['mean'],'sub_mean':st(sub)['mean'],'beau_mean':st(beau)['mean'],
  'beau_minus_add_mean':round(float(beau.mean()-add.mean()),4),
  'max3_minus_add_mean':round(float(mx.mean()-add.mean()),4),
  'note':'the published null used the ADD arm as the ceiling for a BEAUFORT real cell'}
json.dump(out,open('results/av5_verify_frontier5.json','w'),indent=1)
print(json.dumps(out,indent=1))
