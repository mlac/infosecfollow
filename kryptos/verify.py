"""One command to re-establish trust in this whole directory.
Run:  OMP_NUM_THREADS=1 python3 verify.py
Every check below is a POSITIVE CONTROL: a claim that a solver recovers a known answer. If any of
these fail, treat every negative in OVERNIGHT_RESULTS.md as void."""
import numpy as np, subprocess, sys, itertools, os
from lib import *

MISSING = [f for f in ('words.txt', 'quadgrams.npy') if not os.path.exists(f)]
if MISSING:
    print(f"Missing regenerable inputs: {', '.join(MISSING)} (they are gitignored -- ~6 MB of "
          f"derived data).\nRebuild them first:\n  pip install numpy wordfreq\n"
          f"  python3 rebuild_dict.py     # words.txt, 289,026 words\n"
          f"  python3 build_model.py      # quadgrams.npy, ~2 min")
    sys.exit(2)
ok = True
def chk(name, cond, detail=''):
    global ok; ok &= bool(cond)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail else ''))

print("=== 1. harness: all seven solved puzzles round-trip ===")
r = subprocess.run([sys.executable, 'controls.py'], capture_output=True, text=True)
chk("controls.py", r.returncode == 0, r.stdout.strip().splitlines()[-1].strip())

print("=== 2. PK3's key IS a two-word product (so the product family is the series' signature) ===")
chk("q3enc(PT3,[PENTIMENTO,ORDINATE]) == CT[pk3]",
    q3enc(PT['pk3'], ['PENTIMENTO','ORDINATE']) == CT['pk3'])

print("=== 3. dictionary contains every known key (a 183k list does NOT) ===")
ws = set(open('words.txt').read().split())
miss = [k for k in ['PROVENANCE','MARGINS','PENTIMENTO','ORDINATE','UNDERLAY','OCHRE','VERDIGRIS',
                    'HANDIWORK','PORTAL','ALCHEMIST','ANNEAL'] if k not in ws]
chk("all known keys present", not miss, f"{len(ws):,} words; missing={miss}")

print("=== 4. product solver recovers the REAL PK3 and PK4 keys ===")
from product2 import load_words, wordmat, to_idx as p2_idx, score_words
byl = load_words(3,16)
for tag, w, a, b in (('pk3','PENTIMENTO',10,8), ('pk3','ORDINATE',8,10),
                     ('pk4','OCHRE',5,9), ('pk4','VERDIGRIS',9,5)):
    sc = score_words(p2_idx(CT[tag], KA), wordmat(byl[a], KA), a, b, 'sub')
    i = byl[a].index(w); rank = int(np.where(np.argsort(-sc) == i)[0][0]) + 1
    chk(f"{tag}: {w} rank 1", rank == 1, f"rank {rank}/{len(sc)} z={(sc[i]-sc.mean())/sc.std():+.1f}")

print("=== 5. crib consistency test recovers PK3's (8,10) and PK1's period 10, 0 false passes ===")
from crib import derive, consistency_multi
K3 = derive(CT['pk3'], PT['pk3'][:36], KA, 'sub')
p3 = [(a,b) for a in range(3,17) for b in range(a+1,17)
      if consistency_multi(K3,[a,b])[1] and consistency_multi(K3,[a,b])[0] >= 5]
chk("PK3 -> (8,10) is a pass", (8,10) in p3, f"passes={p3}")
K1 = derive(CT['pk1'], PT['pk1'][:36], KA, 'sub')
chk("PK1 -> period 10", consistency_multi(K1,[10])[1] and consistency_multi(K1,[10])[0] >= 5)
import random; random.seed(0); bad = tot = 0
for _ in range(120):
    K = derive(CT['pk3'], ''.join(random.choice(KA) for _ in range(36)), KA, 'sub')
    for a in range(3,17):
        for b in range(a+1,17):
            d,c = consistency_multi(K,[a,b])
            if d >= 5: tot += 1; bad += c
chk("0 false passes on random cribs", bad == 0, f"{bad}/{tot}")

print("=== 6. crib-with-columnar recovers PK4's true column order uniquely ===")
from crib_transpo import solve
perm = (6,2,3,5,1,4,0,7); slot = [0]*8
for k,c in enumerate(perm): slot[c] = k
h = solve(CT['pk4'], PT['pk4'][:24], 8, [(5,9)], KA, 'sub')
chk("PK4 slot unique", len(h) == 1 and h[0]['slot'] == slot,
    f"{len(h)} pass(es) of 40320; fp={h[0]['fp']:.1e}" if h else "none")

print("=== 7. blind Hill row solver recovers PK7's true rows ===")
from hill_blind import rows_for, score_rows
R = rows_for(3); o = score_rows(to_idx(CT['pk7'], KA).astype(np.int64), 3, 2, R)
idx = {tuple(r.tolist()): i for i, r in enumerate(R)}; order = np.argsort(-o)
ranks = [int(np.where(order == idx[tuple(r)])[0][0]) + 1 for r in ([10,16,3],[8,9,0],[9,11,15])]
chk("PK7 true rows in top 150", max(ranks) <= 150, f"ranks {ranks} of {len(R)}")

print("=== 8. period scan has power (a true period-45 PK10-length cipher is detected) ===")
rng = np.random.default_rng(1); ENG = ''.join(PT[k] for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7'])
def stat(s,p): return float(np.mean([ioc(s[r::p]) for r in range(p) if len(s[r::p])>3]))
SH = [''.join(rng.permutation(list(CT['pk10']))) for _ in range(200)]
nv = np.array([stat(s,45) for s in SH])
k = rng.integers(0,26,45); pt = ENG[:504]
c = to_str((to_idx(col_enc(pt,(6,2,3,5,1,4,0,7)))[:504] + k[np.arange(504)%45]) % 26)
zt = (stat(c,45)-nv.mean())/nv.std(); zo = (stat(CT['pk10'],45)-nv.mean())/nv.std()
chk("power at p=45", zt > 5, f"true-cipher z={zt:+.1f}, observed PK10 z={zo:+.1f}")

print("\n" + ("ALL CONTROLS PASS — the negatives in OVERNIGHT_RESULTS.md are trustworthy"
               if ok else "*** A CONTROL FAILED — do not trust the negatives ***"))
sys.exit(0 if ok else 1)
