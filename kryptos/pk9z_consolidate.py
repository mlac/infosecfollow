import json,glob,os
R={}
for f in ['pk9_localization','pk9_split','pk9_likelihood','pk9_power','pk9_posterior_k',
          'pk9_positive_control','pk9_partition','pk9_deconv','pk9_wordset','pk9_wordset_autopsy']:
    p=f'results/{f}.json'
    if os.path.exists(p): R[f]=json.load(open(p))
lik=R['pk9_likelihood']['rows']; pw={r['name']:r for r in R['pk9_power']['rows']}
surv=[];excl_ioc=[];excl_per=[]
for r in lik:
    if abs(r['z_ioc'])>=2: excl_ioc.append((r['name'],round(r['z_ioc'],2))); continue
    nm=r['name']
    alias=[nm, nm.replace('(key letters iid)','(iid key)'),
           nm.replace('(DISTINCT key letters)','(DISTINCT letters)'),
           nm.replace('key, only ','key, '),
           nm.replace('running key thru independent keyed alphabet','running key thru keyed alphabet'),
           nm.replace('Quagmire-III style: keyed alpha','Quagmire-III keyed alpha')]
    p=next((pw[a] for a in alias if a in pw),None)
    if p and p['power']>=0.60: excl_per.append((r['name'],round(r['z_ioc'],2),p['power']))
    else: surv.append((r['name'],round(r['z_ioc'],2), p['power'] if p else None))
out=dict(
 observed=dict(n=144,ioc=0.044484,chi2_uniform=47.39,chi2_uniform_identity="26*(n-1)*IoC+26-n, exact",
   chi2_english_rawAZ=1071.4,chi2_english_sorted=52.8,maxcount=13,mincount=1,
   ioc_z_vs_flat_key=3.18,note="chi2-vs-uniform and IoC are the same statistic; chi2-vs-English in raw order is not substitution-invariant and only says 'a substitution is present' (PK2, a pure transposition, scores 33.8)."),
 map_effective_alphabets=5, credible_set_k="3..14 (95%)",
 excluded_by_ioc=excl_ioc, excluded_by_residue_test=excl_per, surviving=surv,
 localization="no residue-class structure (familywise p=0.124); weak contiguous-block signal at k=3 (z=+3.74, within-family p=0.0062, 4-family global p=0.034); changepoint p=0.50, trend p=0.21",
 positive_control=R['pk9_positive_control'],
 headline_hit=dict(search="278,136-word keystream-letter-set census test, KA alphabet",
   best=14.496, best_words=["CADDY","CADY","CYCAD"],
   flat_key_null_max=11.21, matched_null_max=17.24, above_ceiling=False,
   diagnosis="the winning word's letter set {C,A,D,Y} IS the unrestricted maximum-likelihood 4-subset (score 14.50 identical); with 278k words the dictionary covers essentially every plausible 4-set, so matching the ML subset is automatic"))
json.dump(out,open('results/pk9_anomaly.json','w'),indent=1)
print(f"SURVIVING ({len(surv)}):")
for s in surv: print("   ",s)
print(f"\nEXCLUDED BY IoC ({len(excl_ioc)}):")
for s in excl_ioc: print("   ",s)
print(f"\nEXCLUDED BY THE RESIDUE TEST ({len(excl_per)}):")
for s in excl_per: print("   ",s)
