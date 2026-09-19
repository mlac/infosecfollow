"""BOOT step 1b/3: quadgram model + dictionary from wordfreq (no network needed)."""
import numpy as np, random, math, json
from wordfreq import top_n_list, word_frequency
from lib import AZ, AZI, ioc

random.seed(20260903)
words = [w.upper() for w in top_n_list('en', 200000) if w.isalpha() and w.isascii()]
print("words:", len(words))
freqs = np.array([word_frequency(w.lower(), 'en') for w in words])
freqs = np.maximum(freqs, 1e-9); p = freqs / freqs.sum()

# --- sample a corpus by frequency so cross-word quadgrams are represented ---
N_TOK = 3_000_000
idx = np.random.default_rng(20260903).choice(len(words), size=N_TOK, p=p)
corpus = ''.join(words[i] for i in idx)
print("corpus letters:", len(corpus))

a = np.array([AZI[c] for c in corpus], dtype=np.int64)
k = a[:-3]*17576 + a[1:-2]*676 + a[2:-1]*26 + a[3:]
cnt = np.bincount(k, minlength=456976).astype(np.float64)
print("distinct quadgrams:", int((cnt > 0).sum()), "/456976")
FLOOR = 0.01
qg = np.log10((cnt + FLOOR) / (cnt.sum() + FLOOR*456976))
np.save('quadgrams.npy', qg)

# --- dictionary by length, in KA and AZ index space ---
byl = {}
for w in words:
    byl.setdefault(len(w), []).append(w)
meta = {L: len(byl.get(L, [])) for L in range(3, 17)}
print("dict sizes 3..16:", meta)
np.save('dict_meta.npy', np.array([meta[L] for L in range(3,17)]))
with open('words.txt', 'w') as f:
    f.write('\n'.join(words))

# --- calibration ---
from lib import qscore
print("\n=== CALIBRATION ===")
def sample_eng(n):
    s = ''
    while len(s) < n:
        s += words[np.random.default_rng(random.randrange(1<<30)).choice(len(words), p=p)]
    return s[:n]
for n in (144, 153, 504):
    vals = [ioc(sample_eng(n)) for _ in range(300)]
    print(f"  English {n:3d}: IoC mean {np.mean(vals):.4f}  p5 {np.percentile(vals,5):.4f}  p95 {np.percentile(vals,95):.4f}")
rnd = [ioc(''.join(random.choice(AZ) for _ in range(500))) for _ in range(300)]
print(f"  Random  500: IoC mean {np.mean(rnd):.4f}  p95 {np.percentile(rnd,95):.4f}")
big = sample_eng(20000)
print(f"  English 20000: IoC {ioc(big):.4f}   quadgram/letter {qscore(big):.3f}")
print(f"  Random  20000: quadgram/letter {qscore(''.join(random.choice(AZ) for _ in range(20000))):.3f}")
for k_ in ('pk8','pk9','pk10'):
    from lib import CT
    print(f"  CT {k_}: IoC {ioc(CT[k_]):.4f}")
