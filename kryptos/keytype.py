"""Transposition-invariant, alphabet-agnostic estimate of the KEY TYPE from ciphertext IoC alone.
Simulates each hypothesis at the exact message length instead of using a closed form."""
import numpy as np
from lib import *
rng = np.random.default_rng(4242)
words = open('words.txt').read().split()
ENG = (PT['pk1']+PT['pk2']+PT['pk3']+PT['pk4']+PT['pk5']+PT['pk6']+PT['pk7'])
ITA = "UNAGOTANTOSOTTILEDALEGGEREQUALUNQUENODO"

def eng(n, r):
    i = r.integers(0, len(ENG)-n); return ENG[i:i+n]

def sim(n, mode, P=None, R=400):
    v = []
    for _ in range(R):
        p = np.array([KAI[c] for c in eng(n, rng)])
        if mode == 'periodic':
            k = rng.integers(0, 26, P)[np.arange(n) % P]
        elif mode == 'running':                      # English key text over English plaintext
            k = np.array([KAI[c] for c in eng(n, rng)])
        elif mode == 'random':
            k = rng.integers(0, 26, n)
        elif mode == 'plain':
            k = np.zeros(n, int)
        v.append(ioc((p+k) % 26))
    return np.array(v)

print("Hypothesis -> ciphertext IoC, simulated at the exact message length (400 reps each)")
print(f"{'n':>5} {'hypothesis':<22}{'mean':>8}{'sd':>8}   observed z for that target")
for n, tag in ((153,'pk8'), (144,'pk9'), (504,'pk10')):
    obs = ioc(CT[tag])
    print(f"--- {tag}  n={n}  observed IoC {obs:.4f} ---")
    rows = [('plaintext (no cipher)', sim(n,'plain')), ('running key (English/English)', sim(n,'running')),
            ('random one-time key', sim(n,'random'))]
    for P in (2,3,4,5,6,7,9,12,18,26,45,63,90):
        rows.append((f'periodic P={P}', sim(n,'periodic',P)))
    for name, v in rows:
        z = (obs-v.mean())/v.std()
        flag = '   <== CONSISTENT' if abs(z) < 2 else ''
        print(f"{n:>5} {name:<22}{v.mean():8.4f}{v.std():8.4f}   z={z:+6.2f}{flag}")
