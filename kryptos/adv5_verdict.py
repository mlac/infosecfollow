"""ADV5 adversarial verification of the word-constrained dual-beam PK10 claim.
Rebuilds the MODE-MATCHED null from scratch and re-derives every z."""
import sys, json, numpy as np, os; sys.path.insert(0,'/home/user/infosecfollow/kryptos')
J=lambda f: json.load(open('results/'+f+'.json'))
def stats(v):
    v=np.asarray(v,dtype=float)
    return dict(n=len(v),mean=round(float(v.mean()),4),sd=round(float(v.std(ddof=1)),4),
                max=round(float(v.max()),4),min=round(float(v.min()),4))
def z(x,s): return round((x-s['mean'])/s['sd'],2)

real=J('wb_dual_real');  az=J('wb_dual_az')
R={(e['kmin'],e['mode']):e['obj'] for e in real if e['tag']=='PK10'}
RAZ={(e['kmin'],e['mode']):e['obj'] for e in az}
addk8=[e['obj'] for e in J('wb_dual_null_k8')]              # claimed "matched" null: mode=add
out={}
out['reproduction']=J('adv5_repro')

# ---- 1. the claimed null, as published (mode add) -------------------------
s_add=stats(addk8)
out['published_null_k8_mode_add']=s_add
out['published_comparison']=dict(
    real_cell='PK10 KA kmin>=8 mode=beau', real_obj=R[(8,'beau')],
    null_mode='add', z_as_published=z(R[(8,'beau')],s_add),
    above_published_null_max=bool(R[(8,'beau')]>s_add['max']),
    excess=round(R[(8,'beau')]-s_add['max'],4))

# ---- 2. the MODE-MATCHED null I rebuilt -----------------------------------
def load(p):
    f='results/adv5_null_%s.json'%p
    return J('adv5_null_%s'%p) if os.path.exists(f) else []
beau=load('beau_k8'); sub=load('sub_k8')
if beau:
    sb=stats([e['obj'] for e in beau])
    out['rebuilt_null_k8_mode_beau']=sb
    out['matched_comparison']=dict(
        real_obj=R[(8,'beau')], null_mode='beau (IDENTICAL to the real cell)',
        z_matched=z(R[(8,'beau')],sb),
        above_matched_null_max=bool(R[(8,'beau')]>sb['max']),
        n_null_replicates_beating_the_real_cell=int(sum(e['obj']>R[(8,'beau')] for e in beau)),
        empirical_p=round(( sum(e['obj']>=R[(8,'beau')] for e in beau)+1)/(len(beau)+1),3))
if sub:
    out['rebuilt_null_k8_mode_sub']=stats([e['obj'] for e in sub])

# ---- 3. mode-maximised null (the burden the real search actually carried) --
if beau and sub:
    m={e['shuffle']:{} for e in beau}
    for e in beau: m.setdefault(e['shuffle'],{})['beau']=e['obj']
    for e in sub:  m.setdefault(e['shuffle'],{})['sub']=e['obj']
    for i,e in enumerate(J('wb_dual_null_k8')): m.setdefault(e['shuffle'],{})['add']=e['obj']
    full=[max(v.values()) for k,v in sorted(m.items()) if len(v)==3]
    if full:
        sm=stats(full)
        real_max=max(R[(8,'add')],R[(8,'sub')],R[(8,'beau')])
        out['mode_maximised_null_k8']=dict(per_shuffle_max_over_3_modes=sm,
            real_max_over_3_modes=real_max, z=z(real_max,sm),
            above=bool(real_max>sm['max']),
            n_null_replicates_beating_real=int(sum(x>real_max for x in full)),
            empirical_p=round((sum(x>=real_max for x in full)+1)/(len(full)+1),3),
            shuffles_used=sorted(k for k,v in m.items() if len(v)==3))
        out['mode_maximised_null_k8']['per_shuffle']= {str(k):v for k,v in sorted(m.items()) if len(v)==3}

# ---- 4. secondary quadgram statistic at kmin=10 mode=sub ------------------
sub10=load('sub_k10')
qn_add=[e['qg'] for e in J('wb_dual_null_k10')]
s_q=stats(qn_add)
rq={(e['kmin'],e['mode']):e['qg'] for e in real if e['tag']=='PK10'}
out['secondary_qg_kmin10_sub']=dict(real_qg=rq[(10,'sub')],
    published_null_mode='add', published_stats=s_q, z_as_published=z(rq[(10,'sub')],s_q))
if sub10:
    sq=stats([e['qg'] for e in sub10]); so=stats([e['obj'] for e in sub10])
    out['secondary_qg_kmin10_sub']['rebuilt_null_mode_sub_qg']=sq
    out['secondary_qg_kmin10_sub']['z_matched']=z(rq[(10,'sub')],sq)
    out['secondary_qg_kmin10_sub']['above_matched_max']=bool(rq[(10,'sub')]>sq['max'])
    out['secondary_qg_kmin10_sub']['rebuilt_null_mode_sub_obj']=so
    out['secondary_qg_kmin10_sub']['obj_z_matched']=z(R[(10,'sub')],so)

# ---- 5. grid size / multiple testing --------------------------------------
out['grid']=dict(real_pk10_dual_cells_at_kmin8=6, detail='3 modes x {KA,AZ}',
    real_pk10_dual_cells_all=len([e for e in real if e['tag']=='PK10'])+len(az),
    published_null_replicate_covers=1, note='each published null replicate is ONE cell (add,KA); the real number reported is the max over the whole grid')
json.dump(out,open('results/adv5_word_beam_verify.json','w'),indent=1)
print(json.dumps(out,indent=1))
