"""Omnibus check: is pk9's n=144 10^7 search elevated as a whole, or only in the one cell that
was cherry-picked?  Every one of the 16 real cells gets its own 40-draw matched null."""
import json, numpy as np
nl=json.load(open('results/mtv_null.json')); bos=nl['best_of_search']; seeds=nl['seeds']
art=json.load(open('results/gromark_L7_mod10.json'))
real={}
for run in art:
    for name,t in run['targets'].items():
        p=name.split('.')
        if p[0]=='pk9' and p[1]=='real' and p[-1]!='CLS':
            real['%s.%s.%s'%(run['rec'],p[2],p[3])]=t['top'][0]['score']
rows=[]
for k in sorted(real):
    rec,a,g=k.split('.')
    v=np.array([bos[rec]['s%d.%s.%s'%(s,a,g)] for s in seeds])
    z=(real[k]-v.mean())/v.std(ddof=1); nge=int((v>=real[k]).sum())
    rows.append({'cell':k,'real':round(real[k],6),'null_mean':round(float(v.mean()),6),
                 'null_sd':round(float(v.std(ddof=1)),6),'null_max':round(float(v.max()),6),
                 'z':round(float(z),2),'n_null_ge_real':nge})
    print('%-14s real=%.6f null=%.6f+-%.6f  z=%+5.2f  nulls>=real: %2d/40'%(k,real[k],v.mean(),v.std(ddof=1),z,nge))
zs=np.array([r['z'] for r in rows])
print('\nmean z over the 16 real cells = %+.2f  (se of mean %.2f)  median %+.2f  cells with z>2: %d'
      %(zs.mean(), 1/np.sqrt(16), np.median(zs), (zs>2).sum()))
print('If pk9 really carried a mod-10 Gromark, ONE cell (the right rec/alphabet/direction) would')
print('be enormous (positive control z ~ +7..+11) and the rest flat.  Observed: max z=+%.2f, and'%zs.max())
print('4 cells scattered at z=+2..+3.4, which is what a 16-fold correlated search on noise makes.')
json.dump({'cells':rows,'mean_z':round(float(zs.mean()),2),'max_z':round(float(zs.max()),2),
           'n_cells_z_gt_2':int((zs>2).sum())}, open('results/mtv_omni.json','w'), indent=1)
