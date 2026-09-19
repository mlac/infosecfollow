import numpy as np, json, time
from lib import *
from derived import derived_texts
from product2 import load_words, wordmat, score_words, pairs
from product2 import to_idx as p2_idx
rng = np.random.default_rng(31)
ENG = ''.join(PT[k] for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7'])
def eng(n): i = rng.integers(0, len(ENG)-n); return ENG[i:i+n]
def stat(s, p): return float(np.mean([ioc(s[r::p]) for r in range(p) if len(s[r::p]) > 3]))

D = derived_texts(); byl = load_words(3, 16)
print(f"{len(D)} derived texts (ordered pair x alphabet x forward/reversed x sign)\n")
res = {}
for tag, (s, an) in D.items():
    n = len(s)
    SH = [''.join(rng.permutation(list(s))) for _ in range(300)]
    # 1) global IoC
    nio = [ioc(x) for x in SH]
    row = {'n': n, 'ioc': round(ioc(s), 5), 'ioc_z': round(float((ioc(s)-np.mean(nio))/max(np.std(nio),1e-9)), 2)}
    # 2) transposition-invariant period scan with power
    best = (-9, None)
    for p in range(2, n//5+1):
        nv = np.array([stat(x, p) for x in SH]); z = (stat(s, p)-nv.mean())/nv.std()
        zs = []
        for _ in range(40):
            pt = eng(n); k = rng.integers(0, 26, p)
            c = to_str((to_idx(col_enc(pt,(6,2,3,5,1,4,0,7)))[:n] + k[np.arange(n)%p]) % 26)
            zs.append((stat(c, p)-nv.mean())/nv.std())
        if z > best[0]: best = (float(z), p, float(np.mean(zs)), float((np.array(zs)>3).mean()))
    row['period_best_z'], row['period_best_p'] = round(best[0], 2), best[1]
    row['period_true_z_at_that_p'], row['period_power'] = round(best[2], 2), best[3]
    res[tag] = row
    print(f"  {tag:16s} n={n:3d} IoC {row['ioc']:.4f} (z{row['ioc_z']:+5.2f}) | best period p={best[1]:3d} "
          f"z={best[0]:+5.2f} (a true one would give {best[2]:+.1f}, power {best[3]:.2f})", flush=True)
json.dump(res, open('results/derived_period.json','w'), indent=1)
print("\n=== two-word product grid on the derived texts (KA/KA/sub + AZ/AZ/sub) ===")
prod = []
for tag, (s, an) in D.items():
    for TA, ta in (('KA', KA), ('AZ', AZ)):
        C = p2_idx(s, ta); Wc = {L: wordmat(byl[L], ta) for L in byl}
        SH = [p2_idx("".join(rng.permutation(list(s))), ta) for _ in range(3)]
        bz = -9; bc = None
        for (a, b) in pairs(3, 14):
            for d_, L, m in (('A', a, b), ('B', b, a)):
                if d_ == 'A' and b % a == 0: continue
                sc = score_words(C, Wc[L], L, m, 'sub')
                z = float((sc.max()-sc.mean())/sc.std())
                nz = max(float((lambda t: (t.max()-t.mean())/t.std())(score_words(x, Wc[L], L, m, 'sub'))) for x in SH)
                if z-nz > bz: bz = z-nz; bc = (a, b, d_, round(z,2), round(nz,2), byl[L][int(sc.argmax())])
        prod.append({'text': tag, 'alpha': TA, 'best_delta': round(bz,2), 'cell': bc})
        print(f"  {tag:16s} {TA}: best (z - null_max) = {bz:+.2f}  cell {bc}", flush=True)
json.dump(prod, open('results/derived_product.json','w'), indent=1)
mx = max(prod, key=lambda r: r['best_delta'])
print(f"\nMax over all derived texts: delta {mx['best_delta']:+.2f} ({mx['text']} {mx['alpha']} {mx['cell']})")
