"""Matched null for the crib battery on the DERIVED coupling texts.  The derived text is
d = c_X -/+ c_Y, so the right null shuffles BOTH source ciphertexts independently and re-derives:
same lengths, same letter multisets, same wrap, same corpus, same offsets, same tests."""
import numpy as np, json, sys, time, importlib
sys.path.insert(0, '.')
sys.argv = ['cb_main.py', 'real', '0', 'pk8', '1', '--nolin']
from lib import KA, AZ, CT
src = open('cb_main.py').read().split("t0 = time.time(); OUT = {}")[0]
G = {'__name__': 'null'}
exec(src, G)
run_one, new_acc = G['run_one'], G['new_acc']

WHICH = [('pk8', 'pk9', -1, 'AZ'), ('pk8', 'pk10', -1, 'KA'), ('pk8', 'pk9', +1, 'KA'),
         ('pk9', 'pk10', -1, 'AZ')]
NS = int(sys.argv[1]) if False else 4
rng = np.random.default_rng(99)
OUT = {}
t0 = time.time()
for X, Y, sg, an in WHICH:
    al = KA if an == 'KA' else AZ
    ai = {c: i for i, c in enumerate(al)}
    tag = f"{X}{'+' if sg > 0 else '-'}{Y}_{an}"
    for k in range(NS):
        A = [ai[c] for c in rng.permutation(list(CT[X]))]
        B = [ai[c] for c in rng.permutation(list(CT[Y]))]
        d = ''.join(al[(A[i] + sg*B[i % len(B)]) % 26] for i in range(len(A)))
        acc = new_acc(); run_one(X, d, acc, f"{tag}_shuf{k}")
        acc['eng_mean'] = acc['eng_sum']/max(acc['eng_n'], 1); acc.pop('eng_sum')
        OUT[f"{tag}_shuf{k}"] = {'rows': acc['rows'], 'w1': acc['n_w1'], 'w2': acc['n_w2'],
                                 'seg': acc['n_seg'], 'sib': len(acc['sibling']),
                                 'per': len(acc['periodic']), 'engmax': acc['eng_best'][0]}
        print(f"[{tag} shuf{k}]", OUT[f"{tag}_shuf{k}"], f"({time.time()-t0:.0f}s)", flush=True)
json.dump({'n_shuffles': NS, 'per_run': OUT, 'wall_sec': round(time.time()-t0, 1)},
          open('results/cb_derived_null.json', 'w'), indent=1, default=str)
print('wrote results/cb_derived_null.json')
