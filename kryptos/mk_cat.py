"""M-C / M-D: keys manufactured by CONCATENATION and by INTERLEAVING two words.

 C : key = W1 + W2  (period a+b).  Positions with i%(a+b) < a carry W1, the rest W2.
     Peeling the correct W1 yields TRUE plaintext on its own positions, so each direction
     is scored by the IoC of that position-subset alone; then a joint top-K confirmation.
 CR: key = W1 + reverse(W2) (period a+b).
 D : key = interleave(W1,W2): even positions cycle W1, odd positions cycle W2.
usage: python3 mk_cat.py <tag> <nshuffle>
"""
import sys, os, time, json; sys.path.insert(0, '.')
import numpy as np
from lib import KA, AZ, CT
import mk_lib as M

TAG = sys.argv[1]; NSH = int(sys.argv[2])
AMIN, AMAX = 3, 12
K = 200
CONFIGS = [('KA','KA','sub'), ('KA','KA','add'), ('AZ','AZ','sub'), ('KA','AZ','sub')]
ALPH = {'KA': KA, 'AZ': AZ}
TARGETS = ['pk8', 'pk9', 'pk10']

byl = M.load_words(AMIN, AMAX)
WM = {ka: {L: M.wordmat(byl[L], ALPH[ka]) for L in byl} for ka in ('KA','AZ')}
WMR = {ka: {L: WM[ka][L][:, ::-1].copy() for L in byl} for ka in ('KA','AZ')}

def layout(kind, n, a, b):
    """return (posA, cmA, posB, cmB, mapA_full, mapB_full) -- full maps place a
    length-a/length-b word over ALL n positions with a dummy 0 where it is inactive."""
    i = np.arange(n)
    if kind in ('C','CR'):
        P = a + b; r = i % P
        posA = np.nonzero(r < a)[0]; posB = np.nonzero(r >= a)[0]
        cmA = r[posA]; cmB = r[posB] - a
        fA = np.zeros(n, dtype=np.int64); fA[posA] = cmA
        fB = np.zeros(n, dtype=np.int64); fB[posB] = cmB
    else:                       # interleave
        posA = np.nonzero(i % 2 == 0)[0]; posB = np.nonzero(i % 2 == 1)[0]
        cmA = (posA // 2) % a; cmB = (posB // 2) % b
        fA = np.zeros(n, dtype=np.int64); fA[posA] = cmA
        fB = np.zeros(n, dtype=np.int64); fB[posB] = cmB
    return posA, cmA, posB, cmB, fA, fB, posA, posB

def joint_masked(C, WA, WB, fA, fB, mA, mB, iA, iB, mode):
    """IoC of the full decrypt when word A only acts on mask mA and B only on mB."""
    n = len(C)
    SA = np.zeros((len(iA), n), dtype=np.int16); SA[:, mA] = WA[iA][:, fA[mA]]
    SB = np.zeros((len(iB), n), dtype=np.int16); SB[:, mB] = WB[iB][:, fB[mB]]
    base = C.astype(np.int16); best = -1.0; bi = bj = 0
    for x in range(SA.shape[0]):
        if mode == 'sub':   R = (base[None,:] - SA[x][None,:] - SB) % 26
        elif mode == 'add': R = (base[None,:] + SA[x][None,:] + SB) % 26
        else:               R = (SA[x][None,:] + SB - base[None,:]) % 26
        v = M.ioc_rows_fast(R); j = int(v.argmax())
        if v[j] > best: best, bi, bj = float(v[j]), x, j
    return best, bi, bj

rng = np.random.default_rng(500 + NSH)
rows = []; executed = 0; t00 = time.time()
for tgt in TARGETS:
    base = CT[tgt]
    reps = [base] if NSH == 0 else [M.shuffled(base, rng) for _ in range(NSH)]
    for ri, ct in enumerate(reps):
        for (ta, ka, md) in CONFIGS:
            C = M.to_idx(ct, ALPH[ta]); n = len(C)
            for kind in ('C','CR','D'):
                t0 = time.time(); bb = None
                for a in range(AMIN, AMAX+1):
                    for b in range(AMIN, AMAX+1):
                        posA, cmA, posB, cmB, fA, fB, mA, mB = layout(kind, n, a, b)
                        WB = WMR[ka][b] if kind == 'CR' else WM[ka][b]
                        sA = M.score_parts(C, WM[ka][a], [(posA, cmA)], md)
                        sB = M.score_parts(C, WB, [(posB, cmB)], md)
                        if sA is None or sB is None: continue
                        _,_,_,zA = M.zstat(sA); _,_,_,zB = M.zstat(sB)
                        iA = np.argsort(-sA)[:K]; iB = np.argsort(-sB)[:K]
                        j, x, y = joint_masked(C, WM[ka][a], WB, fA, fB, mA, mB, iA, iB, md)
                        executed += 1
                        row = {'t':tgt,'r':ri,'cfg':f'{ta}/{ka}/{md}','kind':kind,'a':a,'b':b,
                               'zA':round(zA,3),'zB':round(zB,3),'joint':round(j,5),
                               'wA':byl[a][int(iA[x])],'wB':byl[b][int(iB[y])]}
                        rows.append(row)
                        if bb is None or j > bb['joint']: bb = row
                print(f"{tgt} r{ri} {ta}/{ka}/{md} {kind}: best={bb['joint']:.5f} "
                      f"{bb['wA']}|{bb['wB']} ({bb['a']},{bb['b']}) {time.time()-t0:.0f}s", flush=True)
out = {'tag':TAG,'nshuffle':NSH,'executed':executed,'wall':round(time.time()-t00,1)}
rows.sort(key=lambda r: -r['joint'])
out['top'] = rows[:400]
out['max_by_kind'] = {}
for kind in ('C','CR','D'):
    sub = [r for r in rows if r['kind']==kind]
    out['max_by_kind'][kind] = {'max_joint': sub[0]['joint'], 'row': sub[0]} if sub else None
json.dump(out, open(f'results/mk_cat_{TAG}.json','w'), indent=1)
print('WALL', out['wall'], 'EXECUTED', executed)
