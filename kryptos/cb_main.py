"""CRIB BATTERY, real and matched-null.   usage:  python3 cb_main.py real|null NSHUF [tags]

For every (crib, target, text alphabet, mode, offset) the keystream K = c -/+ crib is derived and
then interrogated for STRUCTURE.  Nothing here scores the crib; everything scores K.

Shift-invariance of the linear checker (used to make all-offsets affordable): for a key structure
k[i]=sum_f u_f[i mod p_f], moving the crib from offset 0 to offset d cyclically permutes the
columns of the incidence matrix A within each factor block.  A column permutation leaves the LEFT
null space {v : vA=0} unchanged, so R is exactly offset-invariant -- one checker per
(crib length, structure) serves every offset.  Proof, not sampling.

The matched null is the identical battery on a random letter-permutation of the same ciphertext:
same length, same letter frequencies, same crib corpus, same offsets, same tests.
"""
import numpy as np, itertools, json, sys, time
sys.path.insert(0, '.')
from lib import KA, AZ, KAI, AZI, CT, load_quadgrams
import cb_lib as cb
from cb_corpus import corpus
from crib_sweep import make_checker

WHICH = sys.argv[1]                      # 'real' | 'null'
NSHUF = int(sys.argv[2]) if len(sys.argv) > 2 else 0
TAGS  = sys.argv[3].split(',') if len(sys.argv) > 3 else ['pk8', 'pk9', 'pk10']
SEED  = int(sys.argv[4]) if len(sys.argv) > 4 else 12345
DO_LIN = '--nolin' not in sys.argv
DERIVED = '--derived' in sys.argv

CORP = corpus(max_open=99999, max_close=99999, max_phrase=99999)
LS   = [4,5,6,7,8,9,10,11,12]
STRUCTS  = [(a, b) for a in range(2, 17) for b in range(a+1, 17)]
STRUCTS += list(itertools.combinations(range(3, 13), 3))
MAXFP = 1e-6
OPEN_OFF = 16                            # openings: offsets 0..15 (allows a short preamble)
qg = load_quadgrams()
CK = {}

def checker(m, st):
    k = (m, st)
    if k not in CK: CK[k] = make_checker(np.arange(m), st)
    return CK[k]

def battery(K, mode, tag, alpha_name, m, meta, acc):
    """K: (N,m) int64 keystreams.  meta: callable(i)->dict describing row i."""
    N = K.shape[0]
    acc['rows'] += N
    # --- cheap exact-structure tests
    per = cb.t_periodic(K)
    for i in np.nonzero(per > 0)[0]:
        acc['periodic'].append(dict(meta(int(i)), p=int(per[i])))
    for name, fn in (('affine', cb.t_affine), ('fib', cb.t_fib)):
        h = fn(K)
        for i in np.nonzero(h)[0]: acc[name].append(meta(int(i)))
    # --- linear multi-period structure (product keys, PK3/PK4 shape)
    for st in (STRUCTS if DO_LIN else ()):
        R2, R13, r2, r13 = checker(m, st)
        fp = (2.0**-r2)*(13.0**-r13)
        if fp > MAXFP: acc['skipped'] += 1; continue
        ok = np.ones(N, bool)
        if r2:  ok &= ((K @ R2.T) % 2 == 0).all(1)
        if r13: ok &= ((K @ R13.T) % 13 == 0).all(1)
        acc['lin_tests'] += N; acc['lin_efp'] += fp*N
        for i in np.nonzero(ok)[0]:
            acc['linear'].append(dict(meta(int(i)), structure=list(st), fp=fp))
    # --- word / English / running-key tests, in BOTH key alphabets
    for kan in ('KA', 'AZ'):
        Kaz = cb.MAP[kan][K]
        cube = cb.isword_cube(Kaz, LS)
        w1, w2, seg = cb.t_words(cube, LS)
        acc['n_w1'] += int(w1.sum()); acc['n_w2'] += int(w2.sum()); acc['n_seg'] += int(seg.sum())
        acc['word_tests'] += N
        for i in np.nonzero(w2)[0]:
            acc['two_words'].append(dict(meta(int(i)), keyalpha=kan,
                                         keystream=''.join(AZ[int(x)] for x in Kaz[i])))
        sib = cb.t_running_sibling(K, kan)
        for i in np.nonzero(sib)[0]:
            acc['sibling'].append(dict(meta(int(i)), keyalpha=kan))
        e = cb.t_english(Kaz, qg)
        if len(e):
            j = int(np.argmax(e))
            if e[j] > acc['eng_best'][0]:
                acc['eng_best'] = (float(e[j]), dict(meta(j), keyalpha=kan,
                                   keystream=''.join(AZ[int(x)] for x in Kaz[j])))
            acc['eng_sum'] += float(e.sum()); acc['eng_n'] += len(e)
            acc['eng_top'].extend([(float(e[i]), dict(meta(int(i)), keyalpha=kan,
                                    keystream=''.join(AZ[int(x)] for x in Kaz[i])))
                                   for i in np.argsort(e)[-3:]])
            acc['eng_top'] = sorted(acc['eng_top'], reverse=True, key=lambda z: z[0])[:25]

def run_one(tag, ct, acc, label):
    n = len(ct)
    bylen = {}
    for s, r, k in CORP:
        if len(s) <= n: bylen.setdefault((len(s), k), []).append(s)
    for aname, alpha in (('KA', KA), ('AZ', AZ)):
        ai = {c: i for i, c in enumerate(alpha)}
        Cv = np.array([ai[c] for c in ct], dtype=np.int64)
        for (m, kind), subs in bylen.items():
            if kind == 'open':    offs = np.arange(0, min(OPEN_OFF, n-m+1))
            elif kind == 'close': offs = np.arange(max(0, n-m-OPEN_OFF+1), n-m+1)
            else:                 offs = np.arange(0, n-m+1)
            P = np.array([[ai[c] for c in s] for s in subs], dtype=np.int64)
            Wm = Cv[offs[:, None] + np.arange(m)[None, :]]
            for mode in ('sub', 'add', 'beau'):
                if mode == 'sub':   K = (Wm[:, None, :] - P[None, :, :]) % 26
                elif mode == 'add': K = (P[None, :, :] - Wm[:, None, :]) % 26
                else:               K = (Wm[:, None, :] + P[None, :, :]) % 26
                K = K.reshape(-1, m)
                nc = len(subs)
                def meta(i, subs=subs, offs=offs, nc=nc, mode=mode, aname=aname, kind=kind):
                    return {'text': label, 'alpha': aname, 'mode': mode, 'kind': kind,
                            'crib': subs[i % nc], 'offset': int(offs[i // nc])}
                battery(K, mode, tag, aname, m, meta, acc)

def new_acc():
    return {'rows': 0, 'periodic': [], 'affine': [], 'fib': [], 'linear': [], 'two_words': [],
            'sibling': [], 'skipped': 0, 'lin_tests': 0, 'lin_efp': 0.0, 'word_tests': 0,
            'n_w1': 0, 'n_w2': 0, 'n_seg': 0, 'eng_best': (-99.0, None), 'eng_sum': 0.0,
            'eng_n': 0, 'eng_top': []}

t0 = time.time(); OUT = {}
rng = np.random.default_rng(SEED)
if DERIVED:
    # PK8's key may be PK9's PLAINTEXT (design law 4: PK5's key is PK4's plaintext).  Then
    # d = c8 - c9 is PK8's plaintext under PK9's own keystream, so a crib on d interrogates PK9's
    # key directly.  Prior work ran only the LINEAR structure test on these; here they get the
    # word / segmentation / running-key / English tests as well.
    from derived import derived_texts
    for tagd, (s_, an_) in derived_texts().items():
        if 'R' in tagd.split('_')[0]: continue          # skip the reversed variants
        acc = new_acc(); run_one(tagd, s_, acc, tagd)
        acc['wall'] = round(time.time()-t0, 1); acc['eng_mean'] = acc['eng_sum']/max(acc['eng_n'],1)
        acc.pop('eng_sum'); OUT[tagd] = acc
        print(f"[{tagd}] rows={acc['rows']:,} w1={acc['n_w1']} w2={acc['n_w2']} "
              f"seg={acc['n_seg']} sib={len(acc['sibling'])} per={len(acc['periodic'])} "
              f"engmax={acc['eng_best'][0]:.3f} ({time.time()-t0:.0f}s)", flush=True)
    json.dump({'which': 'derived', 'n_cribs': len(CORP), 'wall_sec': round(time.time()-t0, 1),
               'per_text': OUT}, open('results/cb_main_derived.json', 'w'), indent=1, default=str)
    print('wrote results/cb_main_derived.json'); raise SystemExit
for tag in TAGS:
    if WHICH == 'real':
        acc = new_acc(); run_one(tag, CT[tag], acc, tag)
        acc['wall'] = round(time.time()-t0, 1); acc['eng_mean'] = acc['eng_sum']/max(acc['eng_n'],1)
        acc.pop('eng_sum'); OUT[tag] = acc
        print(f"[{tag}] rows={acc['rows']:,} lin_tests={acc['lin_tests']:,} "
              f"periodic={len(acc['periodic'])} linear={len(acc['linear'])} "
              f"w1={acc['n_w1']} w2={acc['n_w2']} seg={acc['n_seg']} sib={len(acc['sibling'])} "
              f"engmax={acc['eng_best'][0]:.3f} ({time.time()-t0:.0f}s)", flush=True)
    else:
        base = np.array(list(CT[tag]))
        for k in range(NSHUF):
            sh = ''.join(rng.permutation(base))
            acc = new_acc(); run_one(tag, sh, acc, f"{tag}_shuf{k}")
            acc['wall'] = round(time.time()-t0, 1); acc['eng_mean'] = acc['eng_sum']/max(acc['eng_n'],1)
            acc.pop('eng_sum'); OUT[f"{tag}_shuf{k}"] = acc
            print(f"[{tag} shuffle {k}] rows={acc['rows']:,} periodic={len(acc['periodic'])} "
                  f"linear={len(acc['linear'])} w1={acc['n_w1']} w2={acc['n_w2']} "
                  f"seg={acc['n_seg']} sib={len(acc['sibling'])} engmax={acc['eng_best'][0]:.3f} "
                  f"({time.time()-t0:.0f}s)", flush=True)

fn = f"results/cb_main_{WHICH}{'' if WHICH=='real' else NSHUF}.json"
json.dump({'which': WHICH, 'n_cribs': len(CORP), 'n_structures': len(STRUCTS),
           'open_offsets': OPEN_OFF, 'wall_sec': round(time.time()-t0, 1), 'per_text': OUT},
          open(fn, 'w'), indent=1, default=str)
print("wrote", fn, f"{time.time()-t0:.0f}s")
