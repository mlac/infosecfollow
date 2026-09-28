"""Crib attack against 'columnar of width W, then a key whose period divides the column length'.

If W | n (column length L = n/W) and the key period p divides L, then the key at ciphertext
position s*L+t depends only on t, NOT on which column landed in slot s. So for every t the nine
ciphertext letters {ct[s*L+t]} must be a SHIFTED COPY, as a multiset, of the nine crib letters
{crib[c + W*t]} -- and the induced column matchings must agree across all t.
That is a permutation-free test: no W! search at all. It is the natural reading of the design law
that PK6-PK10 all have length divisible by 9.
"""
import numpy as np, itertools, json
from lib import KA, AZ, CT, PT, col_enc, q3enc
from crib_sweep import build_cribs

def multiset_ok(A, B):
    """is multiset A a shift of multiset B? return the list of valid shifts"""
    ha = np.bincount(A, minlength=26); hb = np.bincount(B, minlength=26)
    return [u for u in range(26) if np.array_equal(ha, np.roll(hb, u))]

def test(ct, crib, W, alpha, mode):
    n = len(ct)
    if n % W: return None
    L = n // W; m = len(crib)
    T = m // W
    if T < 2: return None
    ai = {c: i for i, c in enumerate(alpha)}
    C = np.array([ai[c] for c in ct]); P = np.array([ai[c] for c in crib])
    shifts = []
    for t in range(T):
        A = C[[s*L + t for s in range(W)]]
        B = P[[c + W*t for c in range(W)]]
        if mode == 'sub':   u = multiset_ok(A, B)
        elif mode == 'add': u = multiset_ok(B, A)
        else:               u = multiset_ok(A, (-B) % 26)
        if not u: return None
        shifts.append(u)
    return shifts

if __name__ == '__main__':
    CRIBS = build_cribs()
    res = []; ntest = 0
    for tag in ('pk8', 'pk9', 'pk10'):
        n = len(CT[tag])
        Ws = [W for W in range(2, 25) if n % W == 0 and n // W >= 4]
        for W in Ws:
            for an, al in (('KA', KA), ('AZ', AZ)):
                for mode in ('sub', 'add', 'beau'):
                    for cr in CRIBS:
                        if len(cr) // W < 2: continue
                        ntest += 1
                        r = test(CT[tag], cr, W, al, mode)
                        if r:
                            res.append({'target': tag, 'W': W, 'alpha': an, 'mode': mode,
                                        'crib': cr, 'T': len(r), 'shifts': [len(x) for x in r]})
    print(f"widths tested: pk8 {[W for W in range(2,25) if 153%W==0 and 153//W>=4]}, "
          f"pk9 {[W for W in range(2,25) if 144%W==0 and 144//W>=4]}, "
          f"pk10 {[W for W in range(2,25) if 504%W==0 and 504//W>=4]}")
    print(f"tests executed: {ntest:,}  passes: {len(res)}")
    for r in res[:25]: print("  HIT", r)
    json.dump({'n_tests': ntest, 'hits': res}, open('results/crib_multiset.json','w'), indent=1)
