"""M-A: single-word manufactured keystreams (word encrypted under itself / its reverse,
concatenation with its reverse, truncation/extension to a length L that is not a multiple
of the word length, progressive square keys, and the KA alphabet used as a running key).

Every construction gives a keystream that is a deterministic function of ONE dictionary word,
so peeling it yields the full plaintext -> score = IoC of the whole decrypt
(transposition-invariant, doctrine 3).  Exhaustive over words of length 3..16.
usage: python3 mk_single.py <tag> <nshuffle>
"""
import sys, os, time, json; sys.path.insert(0, '.')
import numpy as np
from lib import KA, AZ, CT
import mk_lib as M

TAG = sys.argv[1]; NSH = int(sys.argv[2])
LMIN, LMAX = 3, 16
ROUND = [24, 26, 30, 32, 36, 40, 45, 48]
CONFIGS = [(ta, ka, md) for ta in ('KA','AZ') for ka in ('KA','AZ') for md in ('sub','add')]
ALPH = {'KA': KA, 'AZ': AZ}
TARGETS = ['pk8', 'pk9', 'pk10']

byl = M.load_words(LMIN, LMAX)
WM = {ka: {L: M.wordmat(byl[L], ALPH[ka]) for L in byl} for ka in ('KA','AZ')}
WCAT = {ka: {L: np.hstack([WM[ka][L], WM[ka][L][:, ::-1]]) for L in byl} for ka in ('KA','AZ')}

def Lset(a):
    s = set(range(a+1, 2*a)) | set(ROUND)
    return sorted(x for x in s if x > a and x % a != 0 and x <= 48)

def kavec(n, ka):
    ki = {c: i for i, c in enumerate(ALPH[ka])}
    return np.array([ki[KA[i % 26]] for i in range(n)], dtype=np.int16)

def constructions(a, n, ka):
    """yield (name, effective-word-matrix-key, colmap, off)"""
    i = np.arange(n); m = (i % a)
    yield ('plain', 'W', m, None)
    yield ('self2W', 'W', np.stack([m, m]), None)
    yield ('revsum', 'W', np.stack([m, (a-1-m)]), None)
    yield ('catrev', 'C', (i % (2*a)), None)
    yield ('prog', 'W', np.stack([m, (i//a) % a]), None)
    yield ('progrev', 'W', np.stack([m, a-1-((i//a) % a)]), None)
    kv = kavec(n, ka)
    yield ('KArun', 'W', m, kv)
    yield ('KArunrev', 'W', m, kv[::-1].copy())
    yield ('AZrun', 'W', m, (i % 26).astype(np.int16))
    for L in Lset(a):
        mm = (i % L) % a
        yield (f'trunc{L}', 'W', mm, None)
        yield (f'selftrunc{L}', 'W', np.stack([mm, mm]), None)
        yield (f'revtrunc{L}', 'W', np.stack([mm, a-1-mm]), None)

rng = np.random.default_rng(9000 + NSH)
res = {}   # name -> list of records
executed = 0
t00 = time.time()
for tgt in TARGETS:
    base = CT[tgt]
    reps = [base] if NSH == 0 else [M.shuffled(base, rng) for _ in range(NSH)]
    for ri, ct in enumerate(reps):
        for (ta, ka, md) in CONFIGS:
            C = M.to_idx(ct, ALPH[ta]); n = len(C); allpos = np.arange(n)
            t0 = time.time()
            agg = {}
            for a in range(LMIN, LMAX+1):
                for (name, which, cm, off) in constructions(a, n, ka):
                    Wv = WM[ka][a] if which == 'W' else WCAT[ka][a]
                    sc = M.score_parts(C, Wv, [(allpos, cm)], md, off)
                    executed += 1
                    b, mu, sd, z = M.zstat(sc)
                    w = byl[a][int(sc.argmax())]
                    fam = name.rstrip('0123456789') if name[-1].isdigit() else name
                    r = agg.get(fam)
                    if r is None or b > r[0]:
                        agg[fam] = (b, z, w, a, name)
            for fam, (b, z, w, a, name) in agg.items():
                res.setdefault(fam, []).append(
                    {'t': tgt, 'r': ri, 'cfg': f'{ta}/{ka}/{md}', 'ioc': round(b,5),
                     'z': round(z,2), 'w': w, 'a': a, 'name': name})
            print(f"{tgt} r{ri} {ta}/{ka}/{md} done {time.time()-t0:.0f}s "
                  f"max={max(v[0] for v in agg.values()):.5f}", flush=True)

out = {'tag': TAG, 'nshuffle': NSH, 'executed_word_evaluations': executed,
       'wall': round(time.time()-t00,1), 'families': {}}
for fam, rows in res.items():
    rows.sort(key=lambda r: -r['ioc'])
    out['families'][fam] = {'best': rows[0], 'top10': rows[:10],
                            'max_ioc': rows[0]['ioc'],
                            'mean_of_run_maxima': round(float(np.mean([r['ioc'] for r in rows])),5)}
json.dump(out, open(f'results/mk_single_{TAG}.json','w'), indent=1)
print('WALL', out['wall'], 'SEARCHES', executed)
