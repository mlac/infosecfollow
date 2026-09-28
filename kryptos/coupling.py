"""Do any two of PK8/PK9/PK10 share a keystream? Keyless test.

If c_x and c_y use the SAME keystream then c_x - c_y = p_x - p_y, the difference of two English
texts, whose IoC is ~0.043 rather than the ~0.0385 of two independent ciphertexts. This finds a
shared key WITHOUT finding the key, so it is far more sensitive than searching key space.
Also covers frontier item 6: if PK8's key is PK9's PLAINTEXT then d = c8 - c9 = p8 - K9, i.e. d is
PK8's plaintext enciphered under PK9's own keystream -- so d should be attackable even though
PK9's plaintext is unknown.
"""
import numpy as np, itertools, json
from lib import *
rng = np.random.default_rng(5150)
ENG = ''.join(PT[k] for k in ['pk1','pk2','pk3','pk4','pk5','pk6','pk7'])

def diff(x, y, off=0, rev=False, alpha=KA):
    ai = {c: i for i, c in enumerate(alpha)}
    a = [ai[c] for c in CT[x]]; b = [ai[c] for c in CT[y]]
    if rev: b = b[::-1]
    n = min(len(a), len(b))
    return np.array([(a[i] - b[(i+off) % len(b)]) % 26 for i in range(n)])

# --- calibrate: what IoC does a genuine shared-key pair produce, at these lengths? ---
print("=== calibration: IoC of x-y under each hypothesis (400 reps) ===")
for n in (144, 153):
    sh, ind = [], []
    for _ in range(400):
        i = rng.integers(0, len(ENG)-n); j = rng.integers(0, len(ENG)-n)
        p1 = to_idx(ENG[i:i+n]); p2 = to_idx(ENG[j:j+n])
        k = rng.integers(0, 26, n)
        sh.append(ioc((p1 - p2) % 26))                       # shared keystream -> key cancels
        k2 = rng.integers(0, 26, n)
        ind.append(ioc(((p1+k) - (p2+k2)) % 26))              # independent keystreams
    print(f"  n={n}: SHARED key mean {np.mean(sh):.4f} sd {np.std(sh):.4f} | "
          f"INDEPENDENT mean {np.mean(ind):.4f} sd {np.std(ind):.4f}  "
          f"(separation {(np.mean(sh)-np.mean(ind))/np.std(ind):.1f} sd)")
    if n == 144: SH144, IND144 = (np.mean(sh), np.std(sh)), (np.mean(ind), np.std(ind))
    else:        SH153, IND153 = (np.mean(sh), np.std(sh)), (np.mean(ind), np.std(ind))

print("\n=== observed: every ordered pair, every alphabet, forward and reversed, offset 0 ===")
rows = []
for x, y in itertools.permutations(['pk8','pk9','pk10'], 2):
    for alpha, an in ((KA,'KA'), (AZ,'AZ')):
        for rev in (False, True):
            d = diff(x, y, 0, rev, alpha); n = len(d); v = ioc(d)
            mu, sd = (IND144 if n == 144 else IND153)
            smu, ssd = (SH144 if n == 144 else SH153)
            rows.append((f"{x}-{y}", an, 'rev' if rev else 'fwd', n, v,
                         (v-mu)/sd, (v-smu)/ssd))
rows.sort(key=lambda r: -r[5])
print(f"{'pair':<11}{'alph':<5}{'dir':<5}{'n':>5}{'IoC':>8}{'z vs INDEP':>12}{'z vs SHARED':>13}")
for r in rows: print(f"{r[0]:<11}{r[1]:<5}{r[2]:<5}{r[3]:>5}{r[4]:>8.4f}{r[5]:>12.2f}{r[6]:>13.2f}")

print("\n=== all offsets, all pairs (max over offsets, with a matched null) ===")
for x, y in itertools.permutations(['pk8','pk9','pk10'], 2):
    for alpha, an in ((KA,'KA'), (AZ,'AZ')):
        for rev in (False, True):
            L = len(CT[y]); vs = [ioc(diff(x, y, o, rev, alpha)) for o in range(L)]
            # matched null: identical offset scan against letter-shuffled copies of y
            nulls = []
            for _ in range(60):
                sy = ''.join(rng.permutation(list(CT[y])))
                sv = CT[y]; CT[y] = sy
                nulls.append(max(ioc(diff(x, y, o, rev, alpha)) for o in range(L)))
                CT[y] = sv
            best = int(np.argmax(vs))
            print(f"  {x}-{y} {an} {'rev' if rev else 'fwd'}: best IoC {max(vs):.4f} at offset {best}"
                  f"  | null max-over-offsets mean {np.mean(nulls):.4f} max {np.max(nulls):.4f}"
                  f"  -> {'ABOVE CEILING' if max(vs) > np.max(nulls) else 'below ceiling'}")
