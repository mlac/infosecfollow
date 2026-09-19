"""Is the claimed decrypt language-like at all?  Compare its profile to genuine English
windows of the same length and to the family's own positive-control level."""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from lib import PT,ioc,qscore
from collections import Counter
D=json.load(open('results/qk_repro.json'))
rows=[]
for k,r in D.items():
    pt=r['pt']; n=len(pt); c=Counter(pt)
    rows.append({'cell':k,'joint_ioc':r['joint'],'maxletter_pct':round(100*max(c.values())/n,1),
                 'quad_per_letter':round(qscore(pt),3),'keylen':r['keylen'],'ptlen':n,
                 'roundtrip':r['roundtrip']})
# genuine English windows n=144 from the solved sibling plaintexts
eng=[]
for t,p in PT.items():
    for s in range(0,len(p)-144+1,37):
        w=p[s:s+144]; c=Counter(w)
        eng.append((ioc(w),100*max(c.values())/144,qscore(w)))
E=np.array(eng)
out={'claimed_rows':rows,
     'english_n144_windows':{'n':len(eng),
        'ioc_mean':round(float(E[:,0].mean()),5),'ioc_p95':round(float(np.percentile(E[:,0],95)),5),
        'maxletter_pct_mean':round(float(E[:,1].mean()),1),
        'maxletter_pct_max':round(float(E[:,1].max()),1),
        'quad_mean':round(float(E[:,2].mean()),3)}}
print(json.dumps(out,indent=1))
json.dump(out,open('results/qk_degeneracy.json','w'),indent=1)
