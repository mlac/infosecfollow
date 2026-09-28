"""Frontier item 1 (extended): two-word product sweep over the FULL grid,
each cell with a matched null produced by running the identical search on
letter-shuffled copies of the same ciphertext."""
import numpy as np, json, sys, time, os
from lib import KA, AZ, CT
from product2 import load_words, wordmat, to_idx, score_words, pairs

TARGET = sys.argv[1]
NSHUF  = int(sys.argv[2]) if len(sys.argv) > 2 else 5
MAXL   = int(sys.argv[3]) if len(sys.argv) > 3 else 16
byl = load_words(3, MAXL)
PL = pairs(3, MAXL)
ct = CT[TARGET]
rng = np.random.default_rng(90342 + len(ct))
shuffles = [''.join(rng.permutation(list(ct))) for _ in range(NSHUF)]

ALPHAS = {'KA': KA, 'AZ': AZ}
MODES = ['sub', 'add', 'beau']
out = {'target': TARGET, 'n': len(ct), 'nshuf': NSHUF, 'cells': []}
t00 = time.time(); ncfg = 0

for TA in ALPHAS:
  for KAn in ALPHAS:
    Wc = {L: wordmat(byl[L], ALPHAS[KAn]) for L in byl}
    C = to_idx(ct, ALPHAS[TA])
    Cs = [to_idx(s, ALPHAS[TA]) for s in shuffles]
    for mode in MODES:
      t0 = time.time()
      for (a, b) in PL:
        for (tag, L, m) in (('A', a, b), ('B', b, a)):
            if tag == 'A' and b % a == 0: continue     # no decomposition signal
            sc = score_words(C, Wc[L], L, m, mode)
            ncfg += len(sc)
            mu, sd = sc.mean(), sc.std()
            z = (sc - mu) / sd
            o = np.argsort(-z)[:12]
            # matched null: identical search on shuffled ciphertext
            nz = []
            for Cx in Cs:
                s2 = score_words(Cx, Wc[L], L, m, mode)
                nz.append(float(((s2 - s2.mean()) / s2.std()).max()))
                ncfg += len(s2)
            out['cells'].append({
                'TA': TA, 'KA': KAn, 'mode': mode, 'a': a, 'b': b, 'dir': tag,
                'wl': L, 'mod': m, 'n_words': int(len(sc)),
                'best_z': float(z[o[0]]), 'best_ioc': float(sc[o[0]]),
                'mu': float(mu), 'sd': float(sd),
                'null_mean': float(np.mean(nz)), 'null_max': float(np.max(nz)),
                'top': [[byl[L][i], round(float(z[i]), 2), round(float(sc[i]), 5)] for i in o]})
      print(f"{TARGET} {TA}/{KAn}/{mode}: {time.time()-t0:.0f}s  cum {time.time()-t00:.0f}s", flush=True)

out['n_word_evals'] = ncfg
out['wall_sec'] = round(time.time()-t00, 1)
json.dump(out, open(f'results/product2_{TARGET}.json', 'w'))
cells = out['cells']
cells.sort(key=lambda c: -(c['best_z'] - c['null_max']))
print(f"\n=== {TARGET}: {len(cells)} cells, {ncfg:,} word-evaluations, {out['wall_sec']}s ===")
print(f"{'TA':3}{'KA':3}{'mode':5}{'a':>3}{'b':>3}{'d':>2}{'bestz':>7}{'nullmx':>7}{'delta':>7}  top")
for c in cells[:20]:
    print(f"{c['TA']:3}{c['KA']:3}{c['mode']:5}{c['a']:3d}{c['b']:3d}{c['dir']:>2}"
          f"{c['best_z']:7.2f}{c['null_max']:7.2f}{c['best_z']-c['null_max']:7.2f}  "
          + ' '.join(t[0] for t in c['top'][:5]))
