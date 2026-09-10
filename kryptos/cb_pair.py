"""KEY-FREE CROSS-TARGET CRIB TEST.  The setter says PK9 unlocks PK8, and design law 4 already has
one puzzle's key coming from a sibling.  If two targets share a keystream (same key, possibly with
a small phase slip), then a crib A on X and a crib B on Y at the corresponding positions must
satisfy, with NO key model at all,

        A[i] -/+ B[i]  ==  c_X[offX+i] -/+ c_Y[offY+i]      for all i

so the whole corpus x corpus cross-product is a hash join on the 12-letter difference profile:
index every crib by its 12-prefix, then for each crib B look up the A that the ciphertexts demand.
26^-12 = 1.5e-17 per test, so the false-positive budget is empty even at 10^8 tests.
Run against shuffled ciphertexts for the matched null.
"""
import numpy as np, json, sys, time, itertools
sys.path.insert(0, '.')
from lib import KA, AZ, CT
from cb_corpus import corpus

WHICH = sys.argv[1] if len(sys.argv) > 1 else 'real'
NSHUF = int(sys.argv[2]) if len(sys.argv) > 2 else 0
M = 12
OFFS = range(0, 41)
SLIP = range(-4, 5)
CORP = [s for s, r, k in corpus(max_open=99999, max_close=99999, max_phrase=99999) if len(s) >= M]
KINDS = {s: k for s, r, k in corpus(max_open=99999, max_close=99999, max_phrase=99999)}

def run(texts, label, out):
    st = {'text': label, 'n_tests': 0, 'hits': []}
    t0 = time.time()
    for an, al in (('KA', KA), ('AZ', AZ)):
        ai = {c: i for i, c in enumerate(al)}
        pre = {}
        for s in CORP:
            v = tuple(ai[c] for c in s[:M]); pre.setdefault(v, []).append(s)
        # also index the last M letters, for closing cribs
        suf = {}
        for s in CORP:
            v = tuple(ai[c] for c in s[-M:]); suf.setdefault(v, []).append(s)
        Cs = {t: np.array([ai[c] for c in texts[t]]) for t in texts}
        for X, Y in itertools.combinations(sorted(texts), 2):
            cx, cy = Cs[X], Cs[Y]
            for ox in OFFS:
                if ox + M > len(cx): continue
                for r in SLIP:
                    oy = ox + r
                    if oy < 0 or oy + M > len(cy): continue
                    dx = cx[ox:ox+M]; dy = cy[oy:oy+M]
                    for sx in (1, -1):                       # sub / beau on X
                        for sy in (1, -1):                   # sub / beau on Y
                            # K_X = sx*c_X - sx*A ; K_Y = sy*c_Y - sy*B ; equality gives:
                            # A = c_X - sx*sy*(c_Y - B)  -> A = (dx - sx*sy*dy) + sx*sy*B
                            g = sx*sy
                            base = (dx - g*dy) % 26
                            for tbl in (pre, suf):
                                for v, names in tbl.items():
                                    st['n_tests'] += 1
                                    need = tuple((base[i] + g*v[i]) % 26 for i in range(M))
                                    got = pre.get(need)
                                    if got:
                                        st['hits'].append({'alpha': an, 'X': X, 'Y': Y, 'offX': ox,
                                                           'offY': oy, 'sx': sx, 'sy': sy,
                                                           'A': got[:3], 'B': names[:3]})
    st['wall'] = round(time.time()-t0, 1)
    out[label] = st
    print(f"[{label}] tests={st['n_tests']:,} hits={len(st['hits'])} ({st['wall']}s)", flush=True)

t0 = time.time(); OUT = {}
if WHICH == 'real':
    run({t: CT[t] for t in ('pk8', 'pk9', 'pk10')}, 'real', OUT)
else:
    rng = np.random.default_rng(4242)
    for k in range(NSHUF):
        run({t: ''.join(rng.permutation(list(CT[t]))) for t in ('pk8', 'pk9', 'pk10')},
            f'shuf{k}', OUT)
json.dump({'M': M, 'n_cribs': len(CORP), 'offsets': list(OFFS), 'slips': list(SLIP),
           'wall_sec': round(time.time()-t0, 1), 'per_run': OUT},
          open(f'results/cb_pair_{WHICH}.json', 'w'), indent=1, default=str)
print('wrote', f'results/cb_pair_{WHICH}.json', f'{time.time()-t0:.0f}s')
