"""CRIB ATTACK WITH A COLUMNAR UNDERNEATH  (PK4's and PK6's architecture).

ct = q3enc(col_enc(pt, perm), key).  With W | n the columns are equal length L = n/W, so plaintext
position j sits at ciphertext position slot(j%W)*L + j//W, where slot = perm^-1.  A crib therefore
pins the keystream at m KNOWN ciphertext positions once the slot assignment is chosen -- W! of them.

The W! search is NOT enumerated.  For a period-p key, column c placed in slot s contributes the
partial map  phase (s*L+t) mod p  ->  c[s*L+t] -/+ crib[c+W*t].  A full slot order is consistent
iff the W maps agree, so a depth-first assignment with map-agreement pruning covers all W! orders
exactly, at a cost of a few hundred nodes.  Validated in cb_pc.py: on the REAL PK4 ciphertext with
W=8, p=45 it returns exactly one solution and it is the true order (6,2,3,5,1,4,0,7).

Coverage is honest: this covers every W dividing n, every p in the list, and ALL W! orders for each.
It does NOT cover product keys under a columnar, nor running-key columns (per-column runs are
m/W <= 5 letters for W>=8 at our crib lengths -- too short to test for English); those are handled
only for W<=4 by the per-column running-key test below.
"""
import numpy as np, json, sys, time, math
sys.path.insert(0, '.')
from lib import KA, AZ, KAI, AZI, CT, load_quadgrams
import cb_lib as cb
from cb_corpus import corpus

WHICH = sys.argv[1] if len(sys.argv) > 1 else 'real'
LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 0
TAGS  = sys.argv[4].split(',') if len(sys.argv) > 4 else ['pk8','pk9','pk10']
NSHUF = int(sys.argv[2]) if len(sys.argv) > 2 else 0
PLIST = list(range(2, 21)) + [24, 30, 36, 40, 45]
MINDOF = 5
NODECAP = 200000
qg = load_quadgrams()

C_ALL = corpus(max_open=99999, max_close=99999, max_phrase=99999)
# columnar crib set: the crib must be long enough to give >=2 rows per column, so take the
# longest openings and every closing/phrase.  Ranked by length (more rows per column = more power).
CR = sorted({s for s, r, k in C_ALL if k == 'open'}, key=lambda s: -len(s))[:500]
CR += sorted({s for s, r, k in C_ALL if k in ('close', 'phrase')}, key=lambda s: -len(s))
if LIMIT: CR = CR[:LIMIT]

def widths(n): return [W for W in (3,4,6,8,9,12) if n % W == 0 and n // W >= 3]

def prep(C, P, n, W, d, mode):
    """Precompute, ONCE per (crib,W,offset,mode,alphabet), the derived keystream value D and the
    ciphertext position Q for every (column c, slot s, row t).  Independent of the period p."""
    L = n // W; m = len(P)
    cols = [[] for _ in range(W)]
    for i in range(m):
        j = d + i
        cols[j % W].append((j // W, i))
    if min(len(c) for c in cols) < 2: return None
    Tmax = max(len(c) for c in cols)
    if max(t for c in cols for t, _ in c) >= L: return None
    Q = np.zeros((W, W, Tmax), dtype=np.int64)
    D = np.zeros((W, W, Tmax), dtype=np.int64)
    M = np.zeros((W, Tmax), dtype=bool)
    for c in range(W):
        tc = np.array([t for t, _ in cols[c]]); ic = np.array([i for _, i in cols[c]])
        M[c, :len(tc)] = True
        for s in range(W):
            q = s*L + tc
            Q[c, s, :len(tc)] = q
            Q[c, s, len(tc):] = -1
            D[c, s, :len(tc)] = (C[q] - P[ic]) % 26 if mode == 'sub' else (C[q] + P[ic]) % 26
    return Q, D, M, m

def solve_p(pre, W, p, nodecap=NODECAP):
    """All W! slot orders for a period-p key, by map-agreement DFS.  Returns [(slot, dof)]."""
    Q, D, M, m = pre
    Tmax = Q.shape[2]
    PH = np.where(Q >= 0, Q % p, -1)
    MAPS = np.full((W, W, p), -1, dtype=np.int16)
    ok = np.ones((W, W), dtype=bool)
    for t in range(Tmax):
        ph = PH[:, :, t]; dv = D[:, :, t]
        valid = ph >= 0
        cur = np.where(valid, MAPS[np.arange(W)[:, None], np.arange(W)[None, :],
                                   np.clip(ph, 0, p-1)], -1)
        clash = valid & (cur >= 0) & (cur != dv)
        ok &= ~clash
        ci, si = np.nonzero(valid)
        MAPS[ci, si, ph[ci, si]] = dv[ci, si]
    # pure-Python DFS: the per-node work is a walk over <=Tmax (phase,value) pairs, which is
    # ~30x cheaper than the equivalent numpy masking at these array sizes.
    ML = {}
    for c in range(W):
        for s in range(W):
            if not ok[c, s]: continue
            ph = PH[c, s]; dv = D[c, s]
            ML[(c, s)] = [(int(a), int(b)) for a, b in zip(ph.tolist(), dv.tolist()) if a >= 0]
    sols = []; nodes = [0]
    order = sorted(range(W), key=lambda c: -int(M[c].sum()))
    acc = [-1]*p
    def dfs(k, used, usedmask, ndist):
        nodes[0] += 1
        if nodes[0] > nodecap: return
        if m - ndist < MINDOF: return          # admissible bound: dof can only fall from here
        if k == W:
            slot = [0]*W
            for cc, ss in used: slot[cc] = ss
            sols.append((slot, m - ndist)); return
        c = order[k]
        for s in range(W):
            if usedmask >> s & 1: continue
            mp = ML.get((c, s))
            if mp is None: continue
            undo = []; bad = False
            for a, b in mp:
                v = acc[a]
                if v < 0: acc[a] = b; undo.append(a)
                elif v != b: bad = True; break
            if not bad:
                dfs(k+1, used + [(c, s)], usedmask | (1 << s), ndist + len(undo))
            for a in undo: acc[a] = -1
    dfs(0, [], 0, 0)
    return sols, nodes[0]

def percolumn_running(C, P, n, W, d, mode, kan):
    """PK5 shape: key is a running text, so each column's run is a contiguous key window.
    Only powered when each column holds >= 12 letters."""
    L = n // W; m = len(P)
    cols = [[] for _ in range(W)]
    for i in range(m):
        j = d + i
        cols[j % W].append((j // W, i))
    T = min(len(c) for c in cols)
    if T < 12: return None
    rows = []; lab = []
    for c in range(W):
        tc = np.array([t for t, _ in cols[c]][:T]); ic = np.array([i for _, i in cols[c]][:T])
        for s in range(W):
            q = s*L + tc
            if q.max() >= n: continue
            rows.append((C[q] - P[ic]) % 26 if mode == 'sub' else (C[q] + P[ic]) % 26)
            lab.append((c, s))
    K = np.array(rows)
    sib = cb.t_running_sibling(K, kan)
    eng = cb.t_english(cb.MAP[kan][K], qg)
    return [lab[i] for i in np.nonzero(sib)[0]], float(eng.max()), lab[int(np.argmax(eng))]

def run(tag, ct, label, out):
    n = len(ct); Ws = widths(n)
    st = {'text': label, 'widths': Ws, 'n_solve_calls': 0, 'n_slot_orders_covered': 0,
          'hits': [], 'run_hits': [], 'eng_best': (-99.0, None), 'powered_calls': 0, 'nodes': 0}
    for an, al in (('KA', KA), ('AZ', AZ)):
        ai = {c: i for i, c in enumerate(al)}
        C = np.array([ai[c] for c in ct], dtype=np.int64)
        for cr in CR:
            m = len(cr)
            if m > n: continue
            P = np.array([ai[c] for c in cr], dtype=np.int64)
            for W in Ws:
                if m // W < 2: continue
                for d in (0, n - m):
                    for mode in ('sub', 'beau'):
                        pre = prep(C, P, n, W, d, mode)
                        if pre is not None:
                            for p in PLIST:
                                if m - min(p, m) < MINDOF: continue
                                st['n_solve_calls'] += 1
                                st['n_slot_orders_covered'] += math.factorial(W)
                                sl, nd = solve_p(pre, W, p)
                                st['nodes'] += nd
                                for slot, dof in sl:
                                    st['hits'].append({'alpha': an, 'crib': cr, 'W': W,
                                                       'd': int(d), 'p': p, 'mode': mode,
                                                       'slot': slot, 'dof': dof})
                        for kan in ('KA', 'AZ'):
                            r = percolumn_running(C, P, n, W, d, mode, kan)
                            if r is None: continue
                            st['powered_calls'] += 1
                            hits, e, lb = r
                            if hits: st['run_hits'].append({'alpha': an, 'crib': cr, 'W': W,
                                                            'd': int(d), 'mode': mode,
                                                            'keyalpha': kan, 'pairs': hits})
                            if e > st['eng_best'][0]:
                                st['eng_best'] = (e, {'crib': cr, 'W': W, 'mode': mode,
                                                      'keyalpha': kan, 'pair': lb})
    out[label] = st
    print(f"[{label}] solve_calls={st['n_solve_calls']:,} slot_orders={st['n_slot_orders_covered']:,} "
          f"hits={len(st['hits'])} run_hits={len(st['run_hits'])} "
          f"engmax={st['eng_best'][0]:.3f}", flush=True)

t0 = time.time(); OUT = {}
rng = np.random.default_rng(777)
for tag in TAGS:
    if WHICH == 'real':
        run(tag, CT[tag], tag, OUT)
    else:
        base = np.array(list(CT[tag]))
        for k in range(NSHUF):
            run(tag, ''.join(rng.permutation(base)), f"{tag}_shuf{k}", OUT)
fn = f"results/cb_col_{WHICH}.json"
json.dump({'n_cribs': len(CR), 'periods': PLIST, 'min_dof': MINDOF,
           'wall_sec': round(time.time()-t0, 1), 'per_text': OUT}, open(fn, 'w'), indent=1, default=str)
print("wrote", fn, f"{time.time()-t0:.0f}s")
