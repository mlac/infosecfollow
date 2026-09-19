"""How many distinct cipher alphabets does each target's own IoC admit? -- generator-free.

smallmod_census.py answered this for ONE generator (lagged Fibonacci mod m).  But the only property
of that generator the statistic can see is the number of distinct shift values it emits: IoC is a
function of the letter census, and the census of an additively-enciphered text depends on the
keystream only through the multiset of shifts used and how often each is used.  If that is right,
the interval is a property of the HYPOTHESIS CLASS "j distinct alphabets", not of the recurrence --
and it then bears directly on frontier item 0a, whose two surviving shapes for PK9 are

    * an aperiodic keystream drawn from 3-7 distinct letters, and
    * a key of period >= 18 built from only 3-5 distinct letters,

neither of which any residue or period test can see (power 0.03-0.05).  A census test can.

So: three keystream shapes at the same j, deliberately as different from each other as possible.
  iid   : i.i.d. uniform over a random j-subset of Z26 -- aperiodic, maximally unstructured
  perN  : periodic with period N, drawn from a random j-subset -- the second surviving shape
  lagfib: k[i] = (k[i-6] + k[i-5]) mod j -- the generator smallmod_census.py used
If all three agree, the exclusion is generator-independent and covers item 0a directly.
"""
import numpy as np, json
from lib import KA, CT, PT, to_idx, to_str, ioc, col_enc
SRC = ''.join(PT[k] for k in ('pk2','pk3','pk5','pk6','pk7','pk4','pk1'))
OBS = {t: ioc(CT[t]) for t in ('pk8','pk9','pk10')}
NS  = {'pk8':153,'pk9':144,'pk10':504}
NS_SEED = {'pk8': 8, 'pk9': 9, 'pk10': 10}
NSIM = 4000

def sim(N, j, shape, r):
    off = int(r.integers(0, len(SRC)-N))
    p = to_idx(col_enc(SRC[off:off+N], list(r.permutation(9))), KA).astype(np.int64)
    S = r.permutation(26)[:j]                       # the j distinct shift values actually used
    if shape == 'iid':
        k = S[r.integers(0, j, N)]
    elif shape.startswith('per'):
        P = int(shape[3:]); k = np.resize(S[r.integers(0, j, P)], N)
    else:
        v = np.zeros(N, dtype=np.int64); v[:6] = r.integers(0, j, 6)
        for i in range(6, N): v[i] = (v[i-6] + v[i-5]) % j
        k = S[v]
    return ioc(to_str((p + k) % 26, KA))

SHAPES = ['iid', 'per18', 'per36', 'lagfib']
rows, summary = [], {}
for tag, N in NS.items():
    print(f"\n=== {tag}  n={N}  observed IoC {OBS[tag]:.5f} ===", flush=True)
    print(f"  {'j':>2s} " + ' '.join(f"{s:>17s}" for s in SHAPES), flush=True)
    for j in range(2, 27):
        cells = []
        for shape in SHAPES:
            r = np.random.default_rng((NS_SEED[tag]*100000 + j*100 + SHAPES.index(shape)))
            io = np.array([sim(N, j, shape, r) for _ in range(NSIM)])
            pg = float((io >= OBS[tag]).mean()); z = (OBS[tag]-io.mean())/io.std()
            cons = 0.025 <= pg <= 0.975
            rows.append({'target':tag,'j':j,'shape':shape,'mean':round(float(io.mean()),5),
                         'sd':round(float(io.std()),5),'z':round(float(z),2),
                         'p_ge':pg,'consistent':cons})
            cells.append(f"{z:+6.2f}/{'ok ' if cons else 'EXC'}")
        print(f"  {j:2d} " + ' '.join(f"{c:>17s}" for c in cells), flush=True)
    summary[tag] = {s: [x['j'] for x in rows if x['target']==tag and x['shape']==s and x['consistent']]
                    for s in SHAPES}
    for s in SHAPES:
        v = summary[tag][s]
        print(f"  -> {tag} {s:7s}: consistent j = "
              f"{f'{min(v)}-{max(v)}' if v else 'NONE'}  {v}", flush=True)
json.dump({'obs':OBS,'rows':rows,'summary':summary,'nsim':NSIM},
          open('results/alphabet_count.json','w'), indent=1)
