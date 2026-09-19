"""Is the winning cell degenerate? (the prior false lead was a degenerate gcd vector)"""
import sys, json; sys.path.insert(0,'.')
import numpy as np
import adm_engine as E
from lib import CT

out={}
a=9; L=14; n=144
i=np.arange(n); mm=(i%L)%a
# revtrunc: S = W[mm] + W[a-1-mm]  -> symmetric under mm <-> a-1-mm
pairkey=np.minimum(mm, a-1-mm)
out['keystream_structure']={
 'construction':'revtrunc14, a=9  ->  S[i] = W[(i%14)%9] + W[8-((i%14)%9)]',
 'nominal_key_entropy_letters':9,
 'distinct_keystream_symbols':int(len(np.unique(pairkey))),
 'reason':'S is symmetric in mm <-> 8-mm, so the 9 word letters collapse into 5 sums '
          '(W0+W8, W1+W7, W2+W6, W3+W5, 2*W4).',
 'group_sizes_per_period14':[int((pairkey[:14]==g).sum()) for g in range(5)],
 'effective_period':14,
 'effective_distinct_shifts':5,
 'comment':'A period-14 stream that takes only FIVE distinct shift values flattens the '
           'decrypt letter distribution far less than a 9- or 14-valued stream would, so '
           'this cell has a structurally inflated IoC ceiling independent of any key being right.'}

# how many 9-letter words are score-indistinguishable from METALHEAD?
eng=E.Engine()
ka='AZ'; ta='KA'; md='sub'
C=E.to_idx(CT['pk9'],E.ALPH[ta])
Wv=eng.WM[ka][9]
cm=np.stack([mm, a-1-mm])
sc=E.cell_scores(C,Wv,cm,md,None)
words=eng.byl[9]
j=int(sc.argmax()); best=float(sc[j])
ties=np.nonzero(sc>=best-1e-12)[0]
near=np.nonzero(sc>=best-0.0005)[0]
out['identifiability']={
 'cell':'pk9 KA/AZ/sub revtrunc14 a=9','n_words_searched':len(words),
 'best_ioc':round(best,5),'argmax_word':words[j],
 'n_words_with_EXACTLY_the_top_score':int(len(ties)),
 'example_tied_words':[words[k] for k in ties[:12]],
 'n_words_within_0.0005_of_top':int(len(near)),
 'example_near_words':[words[k] for k in near[:15]]}

# the 5-tuple of the winner: any word with the same 5 sums scores identically
Wm=eng.WM['AZ'][9]
sig=np.stack([(Wm[:,0]+Wm[:,8])%26,(Wm[:,1]+Wm[:,7])%26,(Wm[:,2]+Wm[:,6])%26,
              (Wm[:,3]+Wm[:,5])%26,(2*Wm[:,4])%26],1)
w=Wm[j]
same=np.nonzero((sig==sig[j]).all(1))[0]
out['identifiability']['n_words_sharing_the_winners_5tuple']=int(len(same))
out['identifiability']['words_sharing_the_5tuple']=[words[k] for k in same[:20]]

# cell-level heterogeneity: are 'revtrunc' cells systematically higher than 'plain' cells?
fam={}
for (name,which,cmx,off) in E.constructions(9,n,'AZ'):
    Wx=eng.WM['AZ'][9] if which=='W' else eng.WCAT['AZ'][9]
    s=E.cell_scores(C,Wx,cmx,md,off)
    f=name.rstrip('0123456789') if name[-1].isdigit() else name
    fam.setdefault(f,[]).append(float(s.max()))
out['cell_ceiling_by_construction_family_a9_pk9']={k:{'n_cells':len(v),
    'mean_cell_max':round(float(np.mean(v)),5),'max_cell_max':round(float(np.max(v)),5)}
    for k,v in sorted(fam.items(), key=lambda kv:-np.mean(kv[1]))}
out['heterogeneity_note']=('The construction families do NOT share a common null. '
 'revtrunc/selftrunc cells sit systematically above plain cells because their keystreams '
 'take fewer distinct values. An "in-cell z" computed against the words inside ONE cell '
 'therefore cannot be compared across the grid, and cannot be a search-level z.')
json.dump(out, open('results/adm_degeneracy.json','w'), indent=1)
print(json.dumps(out, indent=1)[:4000])
