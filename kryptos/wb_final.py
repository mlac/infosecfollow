import json, glob, os, numpy as np
R='results/'
def L(f):
    return json.load(open(R+f)) if os.path.exists(R+f) else []
def LG(pat):
    out=[]
    for f in sorted(glob.glob(R+pat)): out+=json.load(open(f))
    return out
real=L('wb_dual_real.json')+L('wb_dual_power.json'); az=L('wb_dual_az.json')
n10=L('wb_dual_null_k10.json'); n8=L('wb_dual_null_k8.json')
pr=L('wb_periodic_real.json'); pn=LG('wb_periodic_null_*.json')
cap=L('wb_capacity.json') or json.load(open(R+'wb_capacity.json'))
def stats(a):
    a=np.array(a,dtype=float)
    return dict(n=len(a),mean=round(a.mean(),4),sd=round(a.std(ddof=1),4),
                max=round(a.max(),4),min=round(a.min(),4))
out={'family':'word-constrained dual beam on PK10 (frontier item 5)','beam':100000,
     'alphabet':'KRYPTOS (KA) unless noted','scoring':
     'sum quadgram(pt) + 1.0*sum logP(pt words) + 2.0*sum logP(key words), per letter',
     'capacity': cap}
# ---- dual
d={'positive_controls':[r for r in real if r['tag'].startswith('SYNTH')],
   'pk1_control_beam100k':L('wb_pc1_beam100000.json'),
   'pk1_control_beam20k':L('wb_pc1_beam20000.json'),
   'real':[{k:v for k,v in r.items() if k!='pt'} for r in real if not r['tag'].startswith('SYNTH')],
   'real_AZ':[{k:v for k,v in r.items() if k!='pt'} for r in az]}
if n10: d['matched_null_kmin10_add']={'obj':stats([x['obj'] for x in n10]),
                                      'qg':stats([x['qg'] for x in n10]),
                                      'construction':'20 independent numpy Generator shuffles of the 504 PK10 letters, identical beam/vocab/mode/weights'}
if n8:  d['matched_null_kmin8_add']={'obj':stats([x['obj'] for x in n8]),'qg':stats([x['qg'] for x in n8])}
out['dual']=d
# ---- periodic
p={'positive_controls':[r for r in pr if r['tag'].startswith('PC')],
   'real_best_per_target':{}}
for tag in ('PK10','PK8','PK9'):
    rows=[r for r in pr if r['tag']==tag]
    if rows:
        b=max(rows,key=lambda r:r['obj'])
        p['real_best_per_target'][tag]={k:v for k,v in b.items()}
        p['real_best_per_target'][tag]['cells']=len(rows)
if pn: p['matched_null']={'obj':stats([x['obj'] for x in pn]),'qg':stats([x['qg'] for x in pn]),
        'construction':'20 shuffles of PK10; each replicate takes the MAX over the same 16 periods (L in 25,27,28,30,32,35,36,40,42,45,48,50,54,56,60,63), mode add, beam 100k'}
p['mode_note']=("For a FREE periodic key, 'add' (c=p+k) and 'sub' (c=p-k) are the same search "
  "(substitute k'=-k), and the runs confirm this cell-for-cell; only add/sub and beau are "
  "distinct.  For the DUAL beam all three modes are distinct because negating a key word "
  "does not give another dictionary word.")
out['periodic']=p
# ---- verdict numbers
if n10:
    o=np.array([x['obj'] for x in n10])
    pk10=[r for r in real if r['tag']=='PK10' and r['kmin']==10 and r['mode']=='add']
    if pk10:
        out['headline']={'pk10_kmin10_add_obj':pk10[0]['obj'],'null_mean':round(o.mean(),4),
            'null_max':round(o.max(),4),'z':round((pk10[0]['obj']-o.mean())/o.std(ddof=1),2),
            'above_null_max':bool(pk10[0]['obj']>o.max())}
json.dump(out,open(R+'word_beam_pk10.json','w'),indent=1)
print(json.dumps({k:v for k,v in out.items() if k in('headline',)},indent=1))
print('wrote results/word_beam_pk10.json')
