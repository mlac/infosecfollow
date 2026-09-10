"""M-B: two-word manufactured key with OUTER REPEAT LENGTH L != lcm(a,b).

key K of length L = q3enc(W1 repeated to length L, W2 cycled), applied with period L.
  S[i] = W1[(i%L)%a] + W2[(i%L)%b]
When lcm(a,b) | L this collapses to the plain two-word product (already covered elsewhere);
those cells are SKIPPED.  Decoupled two-direction search + joint top-K confirmation.
usage: python3 mk_two.py <tag> <nshuffle>      nshuffle=0 -> real ciphertext
"""
import sys, os, time, json; sys.path.insert(0, '.')
import numpy as np
from math import lcm
from lib import KA, AZ, CT
import mk_lib as M

TAG = sys.argv[1]; NSH = int(sys.argv[2])
AMIN, AMAX = 3, 11
KMAX = 5; LMAX = 55; K = 150
CONFIGS = [('KA','KA','sub'), ('KA','KA','add')]
ALPH = {'KA': KA, 'AZ': AZ}
TARGETS = ['pk8', 'pk9', 'pk10']

byl = M.load_words(AMIN, AMAX)
WM = {ka: {L: M.wordmat(byl[L], ALPH[ka]) for L in byl} for ka in ('KA','AZ')}

# grid 2: the key is q3enc(W1 repeated, W2 repeated) TRUNCATED/EXTENDED to a length L that is
# NOT a multiple of len(W1) either -- both words are cut mid-word by the outer period.
CELLS = []
ROUND = [24, 26, 28, 30, 32, 36, 40, 45, 48]
for a in range(3, 10):
    for b in range(a+1, 10):
        Ls = set(ROUND) | {a+b, lcm(a,b)-1, lcm(a,b)+1, lcm(a,b)-2, lcm(a,b)+2, 2*a+b, a+2*b}
        for L in sorted(Ls):
            if L < max(a,b)+1 or L > 55: continue
            if L % lcm(a, b) == 0: continue
            if L % a == 0: continue          # multiples of a are grid 1
            CELLS.append((a, b, L))
CELLS = sorted(set(CELLS))
print(f"cells={len(CELLS)} configs={len(CONFIGS)} targets={len(TARGETS)}", flush=True)

rng = np.random.default_rng(1234 + NSH)
out = {'tag': TAG, 'nshuffle': NSH, 'cells': len(CELLS), 'configs': CONFIGS,
       'K': K, 'rows': [], 'executed': 0}
t00 = time.time()
for tgt in TARGETS:
    base = CT[tgt]
    reps = [base] if NSH == 0 else [M.shuffled(base, rng) for _ in range(NSH)]
    for ri, ct in enumerate(reps):
        for (ta, ka, mode) in CONFIGS:
            C = M.to_idx(ct, ALPH[ta]); n = len(C)
            t0 = time.time()
            bestrow = None
            for (a, b, L) in CELLS:
                fa = M.map_mod(n, L, a); gb = M.map_mod(n, L, b)
                pA = M.parts_by_group(gb, fa); pB = M.parts_by_group(fa, gb)
                sA = M.score_parts(C, WM[ka][a], pA, mode) if M.informative(pA) >= 2 else None
                sB = M.score_parts(C, WM[ka][b], pB, mode) if M.informative(pB) >= 2 else None
                if sA is None or sB is None: continue
                bA, mA, dA, zA = M.zstat(sA); bB, mB, dB, zB = M.zstat(sB)
                iA = np.argsort(-sA)[:K]; iB = np.argsort(-sB)[:K]
                j, ii, jj = M.joint_confirm(C, WM[ka][a], WM[ka][b], fa, gb, iA, iB, mode)
                out['executed'] += 1
                row = {'t': tgt, 'r': ri, 'cfg': f"{ta}/{ka}/{mode}", 'a': a, 'b': b, 'L': L,
                       'zA': round(zA,3), 'zB': round(zB,3), 'joint': round(j,5),
                       'wA': byl[a][int(iA[ii])], 'wB': byl[b][int(iB[jj])]}
                if bestrow is None or row['joint'] > bestrow['joint']: bestrow = row
                out['rows'].append(row)
            print(f"{tgt} r{ri} {ta}/{ka}/{mode}: best joint={bestrow['joint']:.5f} "
                  f"{bestrow['wA']}+{bestrow['wB']} L={bestrow['L']} ({time.time()-t0:.0f}s)", flush=True)
out['wall'] = round(time.time()-t00, 1)
# keep only the top rows to bound file size, plus full per-(target,cfg) maxima
out['rows'].sort(key=lambda r: -r['joint'])
out['rows'] = out['rows'][:400]
json.dump(out, open(f'results/mk_two2_{TAG}.json','w'), indent=1)
print('WALL', out['wall'], 'EXECUTED', out['executed'])
