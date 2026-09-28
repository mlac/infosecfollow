"""Independent recount of how many hypotheses this family actually evaluated."""
import json, glob
real=null=0; prim=0; runs=0; cells_by_scale={}
files=sorted(glob.glob('results/gromark_L*_mod*.json'))+sorted(glob.glob('results/gromark_words_L*.json'))
for fn in files:
    for run in json.load(open(fn)):
        runs+=1
        ex=run['executed']
        for name,t in run['targets'].items():
            p=name.split('.')
            if p[1]=='real': real+=1; prim+=ex
            else: null+=1
            key=(t['n'], 'class' if name.endswith('CLS') else 'shift', ex)
            d=cells_by_scale.setdefault(key,[0,0])
            d[0 if p[1]=='real' else 1]+=1
print('artifact files:%d  kernel runs:%d'%(len(files),runs))
print('REAL search cells: %d   NULL search cells: %d'%(real,null))
print('trial decryptions over real cells: %.3e'%prim)
print('\npools (n, statistic, primers-per-cell) -> (real cells, null cells):')
for k in sorted(cells_by_scale):
    print('  n=%-4d %-6s primers=%-9d  real=%-4d null=%-4d   P(real max > null max)=%.3f'
          %(k[0],k[1],k[2],cells_by_scale[k][0],cells_by_scale[k][1],
            cells_by_scale[k][0]/(cells_by_scale[k][0]+cells_by_scale[k][1])))
json.dump({'files':len(files),'kernel_runs':runs,'real_cells':real,'null_cells':null,
  'trial_decryptions_real':prim,
  'pools':{'n%d_%s_p%d'%k:{'real':v[0],'null':v[1]} for k,v in cells_by_scale.items()}},
  open('results/mtv_count.json','w'),indent=1)
