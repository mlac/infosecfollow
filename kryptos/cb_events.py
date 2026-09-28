"""The w2 statistic (two adjacent dictionary words in the derived keystream) double-counts: the
corpus contains many cribs that share a substring at the same ciphertext offset, so ONE accidental
keystream region shows up as many raw hits.  Deduplicate into EVENTS -- hits whose keystreams agree
on >=8 shared absolute ciphertext positions are the same event -- and null the event count, not the
raw count.  Deeper matched null for the one derived text where real showed raw hits."""
import numpy as np, json, sys, time, ast
sys.path.insert(0, '.')
sys.argv = ['cb_main.py', 'real', '0', 'pk8', '1', '--nolin']
from lib import KA, AZ, CT
src = open('cb_main.py').read().split("t0 = time.time(); OUT = {}")[0]
G = {'__name__': 'ev'}; exec(src, G)
run_one, new_acc = G['run_one'], G['new_acc']

def events(hits):
    H = []
    for h in hits:
        if isinstance(h, str): h = ast.literal_eval(h)
        o = h['offset']; ks = h['keystream']
        H.append(({(o+i, c) for i, c in enumerate(ks)}, h))
    par = list(range(len(H)))
    def find(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for i in range(len(H)):
        for j in range(i+1, len(H)):
            if len(H[i][0] & H[j][0]) >= 8:
                par[find(i)] = find(j)
    return len({find(i) for i in range(len(H))})

NS = 12
al = AZ; ai = {c: i for i, c in enumerate(al)}
rng = np.random.default_rng(31337)
res = {'null_raw': [], 'null_events': []}
t0 = time.time()
for k in range(NS):
    A = [ai[c] for c in rng.permutation(list(CT['pk8']))]
    B = [ai[c] for c in rng.permutation(list(CT['pk9']))]
    d = ''.join(al[(A[i] - B[i % len(B)]) % 26] for i in range(len(A)))
    acc = new_acc(); run_one('pk8', d, acc, f'null{k}')
    res['null_raw'].append(acc['n_w2']); res['null_events'].append(events(acc['two_words']))
    print(f"  shuffle {k}: raw w2={acc['n_w2']} events={res['null_events'][-1]} "
          f"({time.time()-t0:.0f}s)", flush=True)
D = json.load(open('results/cb_main_derived.json'))['per_text']['pk8-pk9_AZ']
res['real_raw'] = D['n_w2']; res['real_events'] = events(D['two_words'])
res['null_raw_max'] = max(res['null_raw']); res['null_events_max'] = max(res['null_events'])
res['null_events_mean'] = float(np.mean(res['null_events']))
res['above_null_max'] = res['real_events'] > res['null_events_max']
print("\nREAL pk8-pk9_AZ: raw w2 =", res['real_raw'], " deduplicated EVENTS =", res['real_events'])
print("NULL (12 matched shuffles): raw", res['null_raw'], "\n  events", res['null_events'],
      " mean", round(res['null_events_mean'], 2), " max", res['null_events_max'])
print("ABOVE MATCHED NULL MAX:", res['above_null_max'])
json.dump(res, open('results/cb_derived_events.json', 'w'), indent=1, default=str)
