"""NULL 'D': the null I think is actually right.
A shuffle destroys the fact that there IS a real plaintext underneath. The honest null for
"pk9's key is a single manufactured word" is: a REAL sibling plaintext, encrypted with a key
that is definitely NOT in the family, then run through the byte-identical search. If that
routinely reaches 0.063, the pk9 number means nothing.

Out-of-family keys used (all are real Kryptos design grammar, none is one dictionary word):
  P40 : q3-style two-word product key, period 40 -- exactly PK3's real construction
  P45 : two words added on KA, period 45 -- exactly PK4's real construction
  RUN : running key taken from another sibling's PLAINTEXT -- exactly PK5's construction
  RND : a uniformly random period-37 keystream (no word structure at all)
One config (KA/AZ/sub), matching the config the claimed hit lives in.
"""
import sys, json, time; sys.path.insert(0,'.')
import numpy as np
import adm_engine as E
from lib import PT, CT

CFG=[('KA','AZ','sub')]
eng=E.Engine()
rng=np.random.default_rng(4242)
KAv=E.KA; AZv=E.AZ
words=[w for w in open('words.txt').read().split() if 5<=len(w)<=12]

def enc(pt144, S):
    """encrypt plaintext (indices on KA) with keystream S (mod 26) -> KA string"""
    return ''.join(KAv[(x+s)%26] for x,s in zip(pt144,S))

sources=[k for k in PT if len(PT[k])>=300] + ['pk1','pk4']
reps=[]; t00=time.time()
N=24
for i in range(N):
    src=sources[i%len(sources)]
    off=int(rng.integers(0,len(PT[src])-144))
    pt=E.to_idx(PT[src][off:off+144], KAv)
    kind=['P40','P45','RUN','RND'][i%4]
    if kind=='P40':
        w1=words[int(rng.integers(len(words)))]; w2=words[int(rng.integers(len(words)))]
        A=E.to_idx(w1,AZv); B=E.to_idx(w2,AZv); L=40
        base=np.array([(A[j%len(A)]+B[j%len(B)])%26 for j in range(L)])
        S=base[np.arange(144)%L]
    elif kind=='P45':
        w1=words[int(rng.integers(len(words)))]; w2=words[int(rng.integers(len(words)))]
        A=E.to_idx(w1,KAv); B=E.to_idx(w2,KAv); L=45
        base=np.array([(A[j%len(A)]+B[j%len(B)])%26 for j in range(L)])
        S=base[np.arange(144)%L]
    elif kind=='RUN':
        o2=[k for k in PT if k!=src][int(rng.integers(len(PT)-1))]
        r=int(rng.integers(0,len(PT[o2])-144))
        S=E.to_idx(PT[o2][r:r+144],KAv)
    else:
        L=37; base=rng.integers(0,26,L); S=base[np.arange(144)%L]
    ct=enc(pt,S)
    t0=time.time(); rr=eng.run(ct, configs=CFG)
    reps.append({'i':i,'src':src,'kind':kind,'grid_max':rr['grid_max'],
                 'argmax':rr['argmax']})
    v=np.array([x['grid_max'] for x in reps])
    json.dump({'design':__doc__,'n':len(v),'mean':round(float(v.mean()),5),
      'sd':round(float(v.std(ddof=1)),5) if len(v)>1 else None,
      'min':round(float(v.min()),5),'max':round(float(v.max()),5),
      'real_pk9_same_one_config':0.06313,
      'n_ge_real':int((v>=0.06313).sum()),
      'exact_permutation_p':round((int((v>=0.06313).sum())+1)/(len(v)+1),4),
      'rows':reps}, open('results/adm_null_synth.json','w'), indent=1)
    print(f"{i} {kind} src={src} grid_max={rr['grid_max']} {rr['argmax']['name']} "
          f"a={rr['argmax']['a']} {rr['argmax']['w']} incell_z={rr['argmax']['in_cell_z']} "
          f"({time.time()-t0:.0f}s) runmax={v.max():.5f} n>=real={int((v>=0.06313).sum())}", flush=True)
print('DONE',round(time.time()-t00,1))
