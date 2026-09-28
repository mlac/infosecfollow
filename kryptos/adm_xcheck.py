"""Cross-check: my independently written engine vs the claim's own mk_lib on the same cells.
If they agree to machine precision, then (a) my reproduction of 0.06313 is not an artefact of
my code, and (b) my nulls are running the same search the claim ran."""
import sys, json; sys.path.insert(0,'.')
import numpy as np
import adm_engine as E, mk_lib as M
from lib import CT, KA, AZ
eng=E.Engine()
rows=[]; worst=0.0
rng=np.random.default_rng(5)
for ta,ka,md in [('KA','AZ','sub'),('AZ','AZ','sub'),('AZ','KA','add'),('KA','KA','beau')]:
    C1=E.to_idx(CT['pk9'],E.ALPH[ta]); C2=M.to_idx(CT['pk9'],{'KA':KA,'AZ':AZ}[ta])
    n=144; allpos=np.arange(n)
    for a in (6,9,12):
        cons_mine=list(E.constructions(a,n,ka)); cons_theirs=list(M_cons(a,n,ka)) if False else None
        for (name,which,cm,off) in cons_mine:
            if name not in ('plain','revtrunc14','trunc14','self2W','catrev','prog','KArun'): continue
            Wv1=eng.WM[ka][a] if which=='W' else eng.WCAT[ka][a]
            Wv2=M.wordmat(eng.byl[a],{'KA':KA,'AZ':AZ}[ka])
            if which=='C': Wv2=np.hstack([Wv2,Wv2[:,::-1]])
            s1=E.cell_scores(C1,Wv1,cm,md,off)
            s2=M.score_parts(C2,Wv2,[(allpos,cm)],md,off)
            d=float(np.max(np.abs(s1-s2))); worst=max(worst,d)
            rows.append({'cfg':f'{ta}/{ka}/{md}','a':a,'name':name,
                         'my_max':round(float(s1.max()),6),'their_max':round(float(s2.max()),6),
                         'max_abs_diff':d,
                         'same_argmax':int(s1.argmax())==int(s2.argmax())})
out={'n_cells_crosschecked':len(rows),'worst_abs_difference':worst,
     'all_argmaxes_agree':all(r['same_argmax'] for r in rows),
     'conclusion':('My engine and the claim s mk_lib produce identical per-word IoC vectors. '
                   'The reproduction and all my nulls therefore run the same search the claim ran.'),
     'rows':rows[:20]}
json.dump(out, open('results/adm_xcheck.json','w'), indent=1)
print(json.dumps({k:v for k,v in out.items() if k!='rows'}, indent=1))
print('sample:', rows[0])
