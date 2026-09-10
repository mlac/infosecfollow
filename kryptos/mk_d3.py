"""M-E: depth-3 recursion  key = q3enc(q3enc(W1 repeated to L, W2), W3), applied with period L.
   S[i] = W1[(i%L)%a] + W2[(i%L)%b] + W3[(i%L)%c],  short words only (a,b,c in 3..5).
Decoupled: to score W1, group positions by the JOINT value (g2(i),g3(i)) -- inside such a group
both other words are constant, so the residual is monoalphabetic.  Statistic = decoupled z.
usage: python3 mk_d3.py <tag> <nshuffle>
"""
import sys, os, time, json; sys.path.insert(0,'.')
import numpy as np
from lib import KA, AZ, CT
import mk_lib as M

TAG = sys.argv[1]; NSH = int(sys.argv[2])
CONFIGS = [('KA','KA','sub'), ('KA','KA','add'), ('AZ','AZ','sub'), ('KA','AZ','sub')]
ALPH = {'KA': KA, 'AZ': AZ}
TARGETS = ['pk8','pk9','pk10']
SHORT = (3,4,5)
byl = M.load_words(3,5)
WM = {ka: {L: M.wordmat(byl[L], ALPH[ka]) for L in byl} for ka in ('KA','AZ')}

CELLS = []
for a in SHORT:
    for b in SHORT:
        for c in SHORT:
            for k in (1,2,3,4,5,6,7,8,9,10,12):
                L = k*a
                if L < 4 or L > 48: continue
                CELLS.append((a,b,c,L))
CELLS = sorted(set(CELLS))

rng = np.random.default_rng(77 + NSH)
rows = []; executed = 0; t00 = time.time(); CTS = {}
for tgt in TARGETS:
    base = CT[tgt]
    reps = [base] if NSH==0 else [M.shuffled(base, rng) for _ in range(NSH)]
    for ri, ct in enumerate(reps):
        CTS[(tgt, ri)] = ct
        for (ta,ka,md) in CONFIGS:
            C = M.to_idx(ct, ALPH[ta]); n = len(C); t0 = time.time(); bb = None
            for (a,b,c,L) in CELLS:
                fa = M.map_mod(n,L,a); fb = M.map_mod(n,L,b); fc = M.map_mod(n,L,c)
                zs = []; ws = []
                for (own, o1, o2, la) in ((fa,fb,fc,a),(fb,fa,fc,b),(fc,fa,fb,c)):
                    gv = o1*26 + o2
                    parts = M.keep_informative(M.parts_by_group(gv, own))
                    if len(parts) < 3: zs.append(None); ws.append(None); continue
                    s = M.score_parts(C, WM[ka][la], parts, md)
                    if s is None: zs.append(None); ws.append(None); continue
                    _,_,_,z = M.zstat(s); zs.append(round(z,3)); ws.append(byl[la][int(s.argmax())])
                executed += 1
                good = [z for z in zs if z is not None]
                if not good: continue
                row = {'t':tgt,'r':ri,'cfg':f'{ta}/{ka}/{md}','a':a,'b':b,'c':c,'L':L,
                       'z':zs,'w':ws,'zmax':max(good),'zmin':min(good)}
                rows.append(row)
                if bb is None or row['zmax'] > bb['zmax']: bb = row
            print(f"{tgt} r{ri} {ta}/{ka}/{md}: zmax={bb['zmax']:.2f} {bb['w']} "
                  f"(a,b,c,L)={bb['a']},{bb['b']},{bb['c']},{bb['L']} {time.time()-t0:.0f}s", flush=True)
# ---- stage 2: joint three-word confirmation on the strongest cells (matched in the null) ----
rows.sort(key=lambda r: -r['zmax'])
TOPC = 40; KJ = 80
def joint3(C, Wa, Wb, Wc, fa, fb, fc, ia, ib, ic, mode):
    n = len(C); base = C.astype(np.int16)
    SB = Wb[ib][:, fb].astype(np.int16); SC = Wc[ic][:, fc].astype(np.int16)
    BC = (SB[:, None, :] + SC[None, :, :]).reshape(-1, n) % 26
    best = -1.0; arg = None
    for x in range(len(ia)):
        SA = Wa[ia[x]][fa].astype(np.int16)
        if mode == 'sub':   R = (base[None,:] - SA[None,:] - BC) % 26
        elif mode == 'add': R = (base[None,:] + SA[None,:] + BC) % 26
        else:               R = (SA[None,:] + BC - base[None,:]) % 26
        v = M.ioc_rows_fast(R); j = int(v.argmax())
        if v[j] > best: best, arg = float(v[j]), (x, j // len(ic), j % len(ic))
    return best, arg
seen = {}
joint_rows = []
for row in rows[:TOPC*4]:
    kk = (row['t'], row['r'], row['cfg'])
    if seen.get(kk, 0) >= TOPC: continue
    seen[kk] = seen.get(kk, 0) + 1
    ta, ka, md = row['cfg'].split('/')
    base_ct = CTS[(row['t'], row['r'])]
    C = M.to_idx(base_ct, ALPH[ta]); n = len(C)
    a,b,c,LL = row['a'],row['b'],row['c'],row['L']
    fa=M.map_mod(n,LL,a); fb=M.map_mod(n,LL,b); fc=M.map_mod(n,LL,c)
    sc3=[]
    for (own,o1,o2,la) in ((fa,fb,fc,a),(fb,fa,fc,b),(fc,fa,fb,c)):
        parts=M.keep_informative(M.parts_by_group(o1*26+o2, own))
        sc3.append(M.score_parts(C, WM[ka][la], parts, md) if len(parts)>=3 else None)
    if any(x is None for x in sc3): continue
    ia,ib,ic = [np.argsort(-x)[:KJ] for x in sc3]
    j,arg = joint3(C, WM[ka][a], WM[ka][b], WM[ka][c], fa, fb, fc, ia, ib, ic, md)
    joint_rows.append({**row, 'joint': round(j,5),
                       'words': [byl[a][int(ia[arg[0]])], byl[b][int(ib[arg[1]])], byl[c][int(ic[arg[2]])]]})
    print('  joint3', row['t'], row['cfg'], (a,b,c,LL), round(j,5), joint_rows[-1]['words'], flush=True)
joint_rows.sort(key=lambda r: -r['joint'])
out = {'tag':TAG,'nshuffle':NSH,'cells':len(CELLS),'executed':executed,
       'wall':round(time.time()-t00,1),'top':rows[:300],
       'max_zmax': rows[0]['zmax'] if rows else None,
       'joint_top': joint_rows[:30],
       'max_joint': (joint_rows[0]['joint'] if joint_rows else None)}
json.dump(out, open(f'results/mk_d3_{TAG}.json','w'), indent=1)
print('WALL', out['wall'], 'EXECUTED', executed, 'MAXZ', out['max_zmax'])
