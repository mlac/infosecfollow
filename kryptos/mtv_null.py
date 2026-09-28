"""Rebuild the matched null for the pk9 n=144 / shift-IoC / 10^7-primer search FROM SCRATCH,
with the verifier's OWN seeds (900001..900040), independent of the claim's 1001/2002.

The search that produced the reported hit was, for pk9 at n=144:
    4 recurrences x 2 text alphabets (KA,AZ) x 2 addition directions = 16 cells,
    each cell a FULL 10^7-primer enumeration, statistic = best-of-search IoC.
This reproduces that entire 16-cell search on each of 40 letter-shuffled copies of pk9,
so the null is over BEST-OF-SEARCH, and over the whole 16-cell search as well.
"""
import sys, time, json, os
sys.path.insert(0,'/home/user/infosecfollow/kryptos')
from gk_common import *
from lib import CT

SEEDS = list(range(900001, 900041))
SPEC = os.environ.get('SCRATCH','/tmp/claude-0/-home-user-infosecfollow/88072dfe-db0a-5acd-9caa-27f75aea8fde/scratchpad') + '/mtv.spec'
res = {}
t0 = time.time()
copies = [(s, shuffled(CT['pk9'], s)) for s in SEEDS]
for rec in [0,1,2,3]:
    for half in [0,1]:
        sub = copies[half*20:(half+1)*20]
        tg = ''
        for s, txt in sub:
            for aname, alpha in [('KA',KA),('AZ',AZ)]:
                for sname, sg in [('m',-1),('p',+1)]:
                    tg += target('s%d.%s.%s'%(s,aname,sname), 0, sg, idx(txt, alpha))
        sp = header(10, 7, 144, rec, topk=1, enum=1)
        r = run(sp + tg, SPEC)
        assert r['executed'] == 10**7, r['executed']
        for k,v in r['targets'].items():
            res.setdefault(RECS[rec], {})[k] = round(v['top'][0]['score'], 6)
        print('rec=%s half=%d done %.0fs'%(RECS[rec], half, time.time()-t0), flush=True)
json.dump({'seeds':SEEDS,'primers_per_cell':10**7,
           'cells_executed':len(SEEDS)*16,'wall_sec':round(time.time()-t0,1),
           'best_of_search':res}, open('results/mtv_null.json','w'), indent=1)
print('WROTE results/mtv_null.json  wall=%.0fs'%(time.time()-t0))
