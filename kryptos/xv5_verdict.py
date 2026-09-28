"""XV5 - final adversarial verdict on frontier item 5 (word-constrained dual beam
on PK10, plus the periodic variant).  Rebuilds every z from raw score lists."""
import json, numpy as np, os
R = '/home/user/infosecfollow/kryptos/results/'
def L(f):
    try: return json.load(open(R+f))
    except Exception: return None

def stats(v):
    v = np.asarray(v, dtype=float)
    return dict(n=int(v.size), mean=round(float(v.mean()),4),
                sd=round(float(v.std(ddof=1)),4), max=round(float(v.max()),4),
                min=round(float(v.min()),4))

def z(x, v):
    v = np.asarray(v, dtype=float)
    return round(float((x - v.mean())/v.std(ddof=1)), 2)

real = {r['mode']: r['obj'] for r in L('wb_dual_real.json')
        if r['tag']=='PK10' and r['kmin']==8}
realq = {r['mode']: r['qg'] for r in L('wb_dual_real.json')
        if r['tag']=='PK10' and r['kmin']==8}
real10 = {r['mode']: r['obj'] for r in L('wb_dual_real.json')
        if r['tag']=='PK10' and r['kmin']==10}
az = L('wb_dual_az.json') or []
real_all_cells = ([r['obj'] for r in L('wb_dual_real.json') if r['tag']=='PK10']
                  + [r['obj'] for r in az])
BEST = max(real_all_cells)

pub8 = [r['obj'] for r in L('wb_dual_null_k8.json')]      # published: mode 'add' ONLY
pub10 = [r['obj'] for r in L('wb_dual_null_k10.json')]    # published: mode 'add' ONLY

xv = L('xv5_null_k8.json') or []
out = {
 'claimed_best_cell': {'alphabet':'KA','kmin':8,'mode':'beau','obj':real.get('beau'),
                       'qg':realq.get('beau')},
 'reproduction': L('xv5_repro.json') and {k:v for k,v in L('xv5_repro.json')[0].items()
                                          if k not in ('pt','key','pt_words','key_words')},
 'published_null_k8_ADD_ONLY': stats(pub8),
 'published_null_k10_ADD_ONLY': stats(pub10),
 'real_cells_kmin8_KA': real, 'real_cells_kmin10_KA': real10,
 'best_over_all_real_PK10_dual_cells': round(BEST,4),
 'n_real_PK10_dual_cells': len(real_all_cells),
}
out['z_as_published'] = {
  'beau_real_vs_ADD_null': z(real['beau'], pub8),
  'note': 'this is the published comparison: a beaufort real cell against an add-mode null'
}
if xv:
    for m in ('add','sub','beau'):
        out.setdefault('xv5_independent_null_k8', {})[m] = stats([r[m] for r in xv])
    m3 = [r['max3'] for r in xv]
    out['xv5_independent_null_k8']['max3'] = stats(m3)
    d = np.array([r['beau']-r['add'] for r in xv])
    out['xv5_mode_effect_paired_beau_minus_add'] = dict(
        mean=round(float(d.mean()),4), sd=round(float(d.std(ddof=1)),4), n=int(d.size))
    out['z_rebuilt'] = {
      'beau_real_vs_BEAU_null': z(real['beau'], [r['beau'] for r in xv]),
      'add_real_vs_ADD_null':   z(real['add'],  [r['add'] for r in xv]),
      'sub_real_vs_SUB_null':   z(real['sub'],  [r['sub'] for r in xv]),
      'max3_real_vs_MAX3_null': z(max(real.values()), m3),
      'nulls_beating_real_max3': f"{int((np.array(m3)>=max(real.values())).sum())}/{len(m3)}",
      'empirical_p_max3': round(float((np.array(m3)>=max(real.values())).mean()),3),
    }
# periodic variant
per = L('wb_periodic_real.json'); pn = (L('wb_periodic_null_0.json') or []) + (L('wb_periodic_null_10.json') or [])
if per and pn:
    p10 = [r for r in per if r['tag']=='PK10']
    b = max(p10, key=lambda r: r['obj'])
    nv = [r['obj'] for r in pn]
    out['periodic'] = {'n_real_cells': len(p10),
        'best': {k:v for k,v in b.items() if k not in ('pt','key')},
        'null_ADD_ONLY_max_over_16_periods': stats(nv),
        'z': z(b['obj'], nv),
        'nulls_beating_real': f"{int((np.array(nv)>=b['obj']).sum())}/{len(nv)}",
        'positive_control_obj': [r['obj'] for r in per if r['tag'].startswith('PC')]}
json.dump(out, open(R+'xv5_frontier5_verdict.json','w'), indent=1)
print(json.dumps(out, indent=1))
