"""Exact copy-label permutation test on the artifacts as they stand.

Under H0 the label (real / nul1 / nul2) is exchangeable within each search cell, because all
three copies have the same length and the same letter multiset and are run through the identical
10^7-primer enumeration.  So permute the copy label and recompute the reported statistic
('max best-of-search over the cells of this search').  Correlation across recurrences/signs is
preserved exactly, because relabelling is applied per (recurrence, alphabet, sign) config.
"""
import sys, json, itertools, glob
sys.path.insert(0,'/home/user/infosecfollow/kryptos')

def load(fn):
    return json.load(open(fn))

def collect(files, ct, nfilter=None):
    """-> {(rec,alpha,sign): {copy: best}}"""
    cells = {}
    for fn in files:
        for run in load(fn):
            rec = run['rec']; L = run['L']; mod = run['mod']
            for name, t in run['targets'].items():
                p = name.split('.')
                if p[0] != ct or p[-1] == 'CLS': continue
                if nfilter and t['n'] != nfilter: continue
                key = (L, mod, rec, p[2], p[3], run.get('tag',''))
                cells.setdefault(key, {})[p[1]] = t['top'][0]['score']
    return cells

files = ['results/gromark_L7_mod10.json']
cells = collect(files, 'pk9')
print('pk9 n=144 L=7 mod=10 full-enumeration configs:', len(cells))
report = {}

def permtest(cells, label):
    keys = sorted(cells)
    trip = [[cells[k][c] for c in ('real','nul1','nul2')] for k in keys]
    obs = max(t[0] for t in trip)
    ge = 0; tot = 0
    for choice in itertools.product(range(3), repeat=len(trip)):
        m = max(trip[i][choice[i]] for i in range(len(trip)))
        tot += 1
        if m >= obs - 1e-12: ge += 1
    print('%-28s configs=%2d  observed_real_max=%.6f  exact p = %d/%d = %.4f'
          % (label, len(trip), obs, ge, tot, ge/tot))
    return {'configs':len(trip),'observed_real_max':round(obs,6),
            'exact_p':round(ge/tot,4),'perms':tot,
            'all_values_sorted':sorted([round(v,6) for t in trip for v in t], reverse=True)[:8]}

report['pk9_all16'] = permtest(cells, 'pk9 all 16 (4rec x 2alpha x 2sign)')
kaonly  = {k:v for k,v in cells.items() if k[3]=='KA'}
report['pk9_KA_8'] = permtest(kaonly, 'pk9 KA only (8 cells)')
nofib   = {k:v for k,v in cells.items() if k[2]!='fib'}
report['pk9_nofib_12'] = permtest(nofib, 'pk9 non-fib (12 cells)')
kanofib = {k:v for k,v in cells.items() if k[3]=='KA' and k[2]!='fib'}
report['pk9_KA_nofib_6'] = permtest(kanofib, 'pk9 KA non-fib (6 cells)')

# single-cell test: the reported cell alone, real vs its own 2 nulls
one = {k:v for k,v in cells.items() if k[2]=='aca' and k[3]=='KA' and k[4]=='m'}
report['pk9_aca_KA_m_alone'] = permtest(one, 'reported cell alone')

# whole-sweep view across every full-enumeration artifact and all three ciphertexts
allfiles = ['results/gromark_L7_mod10.json'] + sorted(glob.glob('results/gromark_L8_mod10_r*.json'))
tot_real = tot_null = 0; above = 0
percell = []
for fn in allfiles:
    for run in load(fn):
        byconf = {}
        for name, t in run['targets'].items():
            p = name.split('.')
            byconf.setdefault((p[0],)+tuple(p[2:]), {})[p[1]] = t['top'][0]['score']
        for conf, d in byconf.items():
            if 'real' not in d: continue
            nulls = [v for c,v in d.items() if c != 'real']
            tot_real += 1; tot_null += len(nulls)
            hit = d['real'] > max(nulls)
            above += hit
            percell.append((run['rec'], conf, d['real'], max(nulls), hit))
print('\nFULL-ENUMERATION sweep (L=7 and L=8, mod 10, all 3 ciphertexts):')
print('  real cells=%d  null cells=%d  above own 2-null ceiling=%d  expected=%.1f (1/3 each)'
      % (tot_real, tot_null, above, tot_real/3.0))
report['full_enum_sweep'] = {'real_cells':tot_real,'null_cells':tot_null,
    'above_own_ceiling':above,'expected_at_p_one_third':round(tot_real/3.0,1),
    'note':'each cell has only TWO matched nulls, so P(real>max of 2)=1/3 under H0'}
json.dump(report, open('results/mtv_perm.json','w'), indent=1)
print('WROTE results/mtv_perm.json')
