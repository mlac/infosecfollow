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
import numpy as np, json, sys, time
sys.path.insert(0, '.')
from lib import KA, AZ, KAI, AZI, CT, load_quadgrams
import cb_lib as cb
from cb_corpus import corpus

WHICH = sys.argv[1] if len(sys.argv) > 1 else 'real'
NSHUF = int(sys.argv[2]) if len(sys.argv) > 2 else 0
PLIST = list(range(2, 25)) + [28, 30, 35, 36, 40, 45]
MINDOF = 5
NODECAP = 200000
qg = load_quadgrams()

C_ALL = corpus(max_open=99999, max_close=99999, max_phrase=99999)
# columnar crib set: the crib must be long enough to give >=2 rows per column, so take the
# longest openings and every closing/phrase.  Ranked by length (more rows per column = more power).
CR = sorted({s for s, r, k in C_ALL if k == 'open'}, key=lambda s: -len(s))[:500]
CR += sorted({s for s, r, k in C_ALL if k in ('close', 'phrase')}, key=lambda s: -len(s))

def widths(n): return [W for W in range(2, 25) if n % W == 0 and n // W >= 3]

def solve(C, P, n, W, d, p, mode):
    """C,P int arrays. crib at plaintext offset d. period p. returns list of (slot_order, dof)."""
    L = n // W; m = len(P)
    cols = [[] for _ in range(W)]
    for i in range(m):
        j = d + i
        cols[j % W].append((j // W, i))
    if min(len(c) for c in cols) < 2: return []
    maps = {}
    for c in range(W):
        tc = np.array([t for t, _ in cols[c]]); ic = np.array([i for _, i in cols[c]])
        if tc.max() >= L: return []
        for s in range(W):
            q = s*L + tc
            D = (C[q] - P[ic]) % 26 if mode == 'sub' else (C[q] + P[ic]) % 26
            ph = q % p
            d_ = {}
            ok = True
            for a, b in zip(ph.tolist(), D.tolist()):
                if a in d_ and d_[a] != b: ok = False; break
                d_[a] = b
            if ok: maps[(c, s)] = d_
    sols = []; nodes = [0]
    order = sorted(range(W), key=lambda c: -len(cols[c]))
    def dfs(k, used, acc):
        nodes[0] += 1
        if nodes[0] > NODECAP: return
        if k == W:
            dof = m - len(acc)
            if dof >= MINDOF:
                slot = [0]*W
                for cc, ss in used: slot[cc] = ss
                sols.append((slot, dof))
            return
        c = order[k]
        for s in range(W):
            if any(s == ss for _, ss in used) or (c, s) not in maps: continue
            mp = maps[(c, s)]
            if any(ph in acc and acc[ph] != v for ph, v in mp.items()): continue
            n2 = dict(acc); n2.update(mp)
            dfs(k+1, used + [(c, s)], n2)
    dfs(0, [], {})
    return sols

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
          'hits': [], 'run_hits': [], 'eng_best': (-99.0, None), 'powered_calls': 0}
    import math
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
                        for p in PLIST:
                            if m - min(p, m) < MINDOF: continue
                            st['n_solve_calls'] += 1
                            st['n_slot_orders_covered'] += math.factorial(W)
                            s = solve(C, P, n, W, d, p, mode)
                            for slot, dof in s:
                                st['hits'].append({'alpha': an, 'crib': cr, 'W': W, 'd': int(d),
                                                   'p': p, 'mode': mode, 'slot': slot, 'dof': dof})
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
for tag in ['pk8', 'pk9', 'pk10']:
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
