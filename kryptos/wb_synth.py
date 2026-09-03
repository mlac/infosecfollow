"""Build the 504-letter positive-control synthetic: real English plaintext
encrypted (add on KA) under a key that is a concatenation of dictionary words."""
import sys, numpy as np, random; sys.path.insert(0,'.')
from lib import KA, PT, q3enc
import wb_core as W
def make(seed=7, n=504, kminL=10, kmaxL=16):
    pt = (PT['pk6'] + PT['pk7'] + PT['pk3'])[:n]
    ws,_ = W.load_vocab(kminL, kmaxL)
    rng = random.Random(seed)
    key = ''
    used = []
    while len(key) < n:
        w = ws[rng.randrange(len(ws))]
        key += w; used.append(w)
    key = key[:n]
    ai={c:i for i,c in enumerate(KA)}
    ct = ''.join(KA[(ai[p]+ai[k])%26] for p,k in zip(pt,key))
    return pt, key, ct, used
if __name__=='__main__':
    pt,key,ct,used=make()
    print('PT ',pt[:80]); print('KEY',key[:80]); print('CT ',ct[:80])
    print('key words:',used[:12]); print(len(pt),len(key),len(ct))
