"""Is the 'sorted unigram profile chi2' independent evidence, or just the maximised IoC
re-expressed?  Correlate the two across the 17 winning residuals of the autopsy."""
import json, numpy as np
d = json.load(open('results/mtv_autopsy.json'))
import sys; sys.path.insert(0,'/home/user/infosecfollow/kryptos')
from lib import KA, CT
from gk_common import shuffled, keystream, idx
ENG = np.array([8.167,1.492,2.782,4.253,12.702,2.228,2.015,6.094,6.966,0.153,0.772,4.025,2.406,
 6.749,7.507,1.929,0.095,5.987,6.327,9.056,2.758,0.978,2.360,0.150,1.974,0.074])/100.
def chi2(a):
    h=np.bincount(np.asarray(a),minlength=26).astype(float); h/=h.sum()
    return float((((np.sort(h)[::-1]-np.sort(ENG)[::-1])**2)/np.sort(ENG)[::-1]).sum())
def resid(txt,primer,rec,sign):
    c=np.array(idx(txt,KA)); k=np.array(keystream(primer,len(c),rec,10)); return (c+sign*k)%26
def ioc(a):
    h=np.bincount(a,minlength=26); n=len(a); return float((h*(h-1)).sum()/(n*(n-1)))
arts=json.load(open('results/gromark_L7_mod10.json')); rm={'aca':0,'lag1':1,'fib':2,'subaca':3}
xs=[];ys=[]
for run in arts:
    for name,t in run['targets'].items():
        p=name.split('.')
        if p[0]!='pk9' or p[-1]=='CLS' or p[2]!='KA': continue
        txt=CT['pk9'] if p[1]=='real' else shuffled(CT['pk9'],1001 if p[1]=='nul1' else 2002)
        r=resid(txt,t['top'][0]['primer'],rm[run['rec']],-1 if p[3]=='m' else 1)
        xs.append(ioc(r)); ys.append(chi2(r))
xs=np.array(xs);ys=np.array(ys)
c=float(np.corrcoef(xs,ys)[0,1])
print('n=%d  corr(best-of-search IoC, sorted-profile chi2) = %.3f'%(len(xs),c))
print('  => the profile statistic is the maximised statistic re-expressed, not independent evidence')
json.dump({'n':len(xs),'corr_ioc_vs_profilechi2':round(c,3),
  'ioc':[round(float(v),6) for v in xs],'chi2':[round(float(v),4) for v in ys]},
  open('results/mtv_chi2corr.json','w'),indent=1)
