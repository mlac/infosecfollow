"""A key SHORTER than the message wraps. If PK8's key is PK9's plaintext (144 letters on a
153-letter message) then k[i] = k[i+144] for i=0..8. No period scan can see that -- at lag 144
there are only 9 pairs. But a crib can: a prefix crib fixes k[0..8] and a suffix crib fixes
k[144..152], and the two must agree EXACTLY on all 9. That is 26^-9 = 5e-13 per pair, so the whole
cross-product of 10,685 x 10,685 cribs can be tested with essentially no false-positive budget.

Implemented as a hash join, not a double loop: the condition
    c[i] - Pre[i] == c[i+Q] - Suf[i + Q - (n - m2)]
rearranges to  Pre[0..k-1] - Suf[tail k] == c[0..k-1] - c[Q..Q+k-1] =: Delta,
so index every crib's head and every crib's tail once and look Delta up.
"""
import numpy as np, json, itertools
from lib import KA, AZ, CT
from crib_sweep import build_cribs

CRIBS = build_cribs()
def run(tag, Qs, modes=('sub','add','beau'), alphas=(('KA',KA),('AZ',AZ))):
    ct = CT[tag]; n = len(ct); hits = []; ntest = 0
    for an, al in alphas:
        ai = {c: i for i, c in enumerate(al)}
        C = np.array([ai[c] for c in ct])
        for mode in modes:
            for Q in Qs:
                k = n - Q                       # number of wrap constraints available
                if k < 6: continue
                # delta over the k overlap positions
                Delta = tuple((C[:k] - C[Q:Q+k]) % 26)
                heads = {}
                for cr in CRIBS:
                    if len(cr) < k: continue
                    h = tuple(ai[x] for x in cr[:k])
                    heads.setdefault(h, []).append(cr)
                for cr in CRIBS:
                    if len(cr) < k: continue
                    t = [ai[x] for x in cr[-k:]]
                    if mode == 'sub':   want = tuple((Delta[i] + t[i]) % 26 for i in range(k))
                    elif mode == 'add': want = tuple((t[i] - Delta[i]) % 26 for i in range(k))
                    else:               want = tuple((-Delta[i] - t[i]) % 26 for i in range(k))
                    ntest += 1
                    if want in heads:
                        for hcr in heads[want]:
                            hits.append({'target': tag, 'alpha': an, 'mode': mode, 'Q': Q,
                                         'k': k, 'prefix_crib': hcr, 'suffix_crib': cr})
    return hits, ntest

out = {}; TOT = 0
for tag in ('pk8', 'pk9', 'pk10'):
    n = len(CT[tag])
    Qs = [Q for Q in range(n-29, n) if n-Q >= 6]
    if tag == 'pk8':  Qs = sorted(set(Qs + [144]))          # the PT9-as-key hypothesis
    if tag == 'pk10': Qs = sorted(set(Qs + [144, 153, 288, 306, 432, 459]))
    h, nt = run(tag, Qs); TOT += nt
    out[tag] = h
    print(f"  {tag}: Q in {min(Qs)}..{max(Qs)} ({len(Qs)} wrap periods), {nt:,} hash-join tests, "
          f"{len(h)} exact agreements", flush=True)
json.dump({'n_cribs': len(CRIBS), 'n_tests': TOT, 'hits': out}, open('results/wrap_crib.json','w'), indent=1)
print(f"\nTOTAL: {TOT:,} tests over {len(CRIBS):,} cribs. "
      f"Expected false positives at 26^-6 (weakest case, k=6): {TOT*26.0**-6:.2e}")
for t in out:
    for h in out[t][:20]: print("  HIT", h)
