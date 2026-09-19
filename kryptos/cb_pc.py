"""POSITIVE CONTROLS for the crib battery: show it RECOVERS the four solved constructions whose
key is crib-visible, at the same message lengths, before any negative is claimed.

PK1  key PROVENANCE repeated      -> t_periodic must say 10, word test must read PROVENANCE
PK3  key q3enc(PENTIMENTOx4,ORDINATE) -> linear (8,10) consistency + two-word recovery
PK4  columnar W8 then key OCHRE+VERDIGRIS -> columnar periodic-assembly must find the slot order
PK5  columnar W8 then RUNNING KEY = PT4  -> per-column runs must read as PT4 / as English
PK6  double columnar then PORTAL (period 6) -> periodic test on the correctly transposed text
"""
import numpy as np, sys, json
sys.path.insert(0, '.')
from lib import KA, AZ, KAI, AZI, CT, PT, col_enc, q3enc, load_quadgrams
import cb_lib as cb
from crib_sweep import make_checker

qg = load_quadgrams()
R = {}

def derive(tag, crib, off, alpha=KA, mode='sub'):
    ai = {c: i for i, c in enumerate(alpha)}
    C = np.array([ai[c] for c in CT[tag]]); P = np.array([ai[c] for c in crib])
    W = C[off:off+len(crib)]
    return ((W - P) % 26 if mode == 'sub' else (W + P) % 26)[None, :]

def two_words(K, off, a, b, alpha=KA):
    """K[j] = u[(off+j)%a] + v[(off+j)%b].  Solve, then look for shifts making both words.
    gcd(a,b)=g splits the residue graph into g components, each with its own free constant,
    so the shift search is over 26^g, not 26."""
    from math import gcd
    m = len(K); g = gcd(a, b)
    if g > 3: return None
    u = {}; v = {}
    for comp in range(g):
        seed = next((r for r in range(a) if r % g == comp), None)
        u[seed] = 0
    for _ in range(4*(a+b)):
        for j in range(m):
            ra, rb = (off+j) % a, (off+j) % b
            if ra in u and rb not in v: v[rb] = (K[j]-u[ra]) % 26
            elif rb in v and ra not in u: u[ra] = (K[j]-v[rb]) % 26
    if len(u) < a or len(v) < b: return None
    uu = np.array([u[i] for i in range(a)]); vv = np.array([v[i] for i in range(b)])
    Wd = cb.words_by_len()
    S = {L: set(Wd[L].tolist()) for L in Wd}
    import itertools as _it
    for cs in _it.product(range(26), repeat=g):
        s1 = ''.join(alpha[(uu[i] + cs[i % g]) % 26] for i in range(a))
        s2 = ''.join(alpha[(vv[i] - cs[i % g]) % 26] for i in range(b))
        c1 = 0
        for ch in s1: c1 = c1*26 + AZI[ch]
        c2 = 0
        for ch in s2: c2 = c2*26 + AZI[ch]
        if a in S and c1 in S[a] and b in S and c2 in S[b]: return (s1, s2)
    return None

# ---------------- PC1: PK1 ----------------
crib = PT['pk1'][:30]
K = derive('pk1', crib, 0)
per = cb.t_periodic(K)[0]
Kaz = cb.MAP['KA'][K]
cube = cb.isword_cube(Kaz, [4,5,6,7,8,9,10,11,12])
w1, w2, seg = cb.t_words(cube, [4,5,6,7,8,9,10,11,12])
keystr = ''.join(KA[int(x)] for x in K[0])
R['PC1_pk1'] = {'crib': crib, 'period_found': int(per), 'period_true': 10,
                'keystream': keystr, 'word_anywhere': bool(w1[0]), 'two_adjacent_words': bool(w2[0]),
                'full_segmentation': bool(seg[0]),
                'PASS': bool(per == 10 and keystr[:10] == 'PROVENANCE' and w1[0])}
print("PC1 PK1 :", R['PC1_pk1'])

# ---------------- PC3: PK3 ----------------
crib = PT['pk3'][:60]
K = derive('pk3', crib, 0)
per = cb.t_periodic(K)[0]
R2, R13, r2, r13 = make_checker(np.arange(60), (8, 10))
lin = bool(((K @ R2.T) % 2 == 0).all() and ((K @ R13.T) % 13 == 0).all())
tw = two_words(K[0], 0, 8, 10)
R['PC3_pk3'] = {'crib': crib, 'period_found': int(per), 'period_true': 40,
                'linear_(8,10)_consistent': lin, 'checks_r2': int(r2), 'checks_r13': int(r13),
                'two_word_recovery': tw, 'PASS': bool(lin and tw is not None and
                                                      set(tw) == {'ORDINATE', 'PENTIMENTO'})}
print("PC3 PK3 :", R['PC3_pk3'])

# ---------------- columnar machinery ----------------
def col_positions(slot, W, L, m):
    return np.array([slot[j % W]*L + j//W for j in range(m)])

def col_periodic_assign(ct, crib, W, p, alpha=KA, mode='sub'):
    """Exact search over ALL W! slot orders for a period-p key, done as a consistency DFS:
    column c placed in slot s contributes the map  phase (s*L+t) mod p -> D[c,s,t].
    Returns every consistent full assignment.  Prunes to milliseconds; no enumeration of W!."""
    n = len(ct); assert n % W == 0
    L = n // W; m = len(crib); T = m // W
    if T < 2: return []
    ai = {c: i for i, c in enumerate(alpha)}
    C = np.array([ai[c] for c in ct]); P = np.array([ai[c] for c in crib])
    maps = {}
    for c in range(W):
        for s in range(W):
            d = {}
            ok = True
            for t in range(T):
                q = s*L + t
                val = (C[q] - P[c + W*t]) % 26 if mode == 'sub' else (C[q] + P[c + W*t]) % 26
                ph = q % p
                if ph in d and d[ph] != val: ok = False; break
                d[ph] = val
            if ok: maps[(c, s)] = d
    sols = []
    def dfs(c, used, acc):
        if c == W: sols.append(list(used)); return
        for s in range(W):
            if s in used or (c, s) not in maps: continue
            d = maps[(c, s)]
            if any(ph in acc and acc[ph] != v for ph, v in d.items()): continue
            n2 = dict(acc); n2.update(d)
            dfs(c+1, used + [s], n2)
    dfs(0, [], {})
    return sols

# ---------------- PC4: PK4 (columnar W8 + period 45) ----------------
true_perm = (6, 2, 3, 5, 1, 4, 0, 7)
slot_true = [0]*8
for s, c in enumerate(true_perm): slot_true[c] = s
sols = col_periodic_assign(CT['pk4'], PT['pk4'][:224], 8, 45)
R['PC4_pk4'] = {'W': 8, 'p': 45, 'n_solutions': len(sols), 'true_slot': slot_true,
                'PASS': slot_true in sols}
print("PC4 PK4 :", {k: v for k, v in R['PC4_pk4'].items()})

# ---------------- PC6: PK6 (period 6) ----------------
t6 = col_enc(col_enc(PT['pk6'], [1,3,0,4,8,2,6,7,5]), [4,2,8,1,6,7,0,3,5])
ai = {c: i for i, c in enumerate(KA)}
K6 = np.array([[(ai[CT['pk6'][i]] - ai[t6[i]]) % 26 for i in range(60)]])
per6 = cb.t_periodic(K6)[0]
R['PC6_pk6'] = {'period_found': int(per6), 'period_true': 6,
                'keystream': ''.join(KA[int(x)] for x in K6[0][:12]),
                'PASS': bool(per6 == 6 and ''.join(KA[int(x)] for x in K6[0][:6]) == 'PORTAL')}
print("PC6 PK6 :", R['PC6_pk6'])

# ---------------- PC5: PK5 (columnar W8 + RUNNING KEY = PT4) ----------------
perm5 = (5, 4, 2, 6, 7, 0, 1, 3)
slot5 = [0]*8
for s, c in enumerate(perm5): slot5[c] = s
n = 272; L = n // 8; crib5 = PT['pk5'][:128]; T = len(crib5)//8
C5 = np.array([KAI[c] for c in CT['pk5']]); P5 = np.array([KAI[c] for c in crib5])
rows = []; labels = []
for c in range(8):
    for s in range(8):
        q = np.array([s*L + t for t in range(T)])
        rows.append((C5[q] - P5[c + 8*np.arange(T)]) % 26); labels.append((c, s))
Kc = np.array(rows)
sib = cb.t_running_sibling(Kc, 'KA', L=12)
eng = cb.t_english(cb.MAP['KA'][Kc], qg)
found = [labels[i] for i in np.nonzero(sib)[0]]
true_pairs = sorted((c, slot5[c]) for c in range(8))
R['PC5_pk5'] = {'W': 8, 'crib_len': len(crib5), 'per_column_letters': int(T),
                'true_column_slot_pairs': true_pairs,
                'sibling_window_hits': sorted(found),
                'eng_true_mean': float(np.mean([eng[i] for i, l in enumerate(labels) if l in true_pairs])),
                'eng_other_mean': float(np.mean([eng[i] for i, l in enumerate(labels) if l not in true_pairs])),
                'PASS': sorted(found) == true_pairs}
print("PC5 PK5 :", {k: v for k, v in R['PC5_pk5'].items() if k != 'sibling_window_hits'})
print("        sibling hits:", sorted(found))

R['ALL_PASS'] = all(v['PASS'] for k, v in R.items() if k.startswith('PC'))
print("\nALL POSITIVE CONTROLS PASS:", R['ALL_PASS'])
json.dump(R, open('results/cb_positive_controls.json', 'w'), indent=1)
