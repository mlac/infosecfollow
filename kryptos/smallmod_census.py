"""Is a small-modulus keystream even CONSISTENT with PK8/PK9/PK10's own IoC?

run_smallmod.py searches for a keystream k[i]=(k[i-L]+k[i-L+1]) mod m, motivated by §G2's estimate
of ~5 effective cipher alphabets on PK9.  Before grading its silence, ask the prior question the
doctrine demands: does the hypothesis reproduce the target's census at all?  A search for a
construction the target's IoC already excludes cannot produce an informative negative.

Forward simulation only -- no key search.  Plaintext is the setter's own seven plaintexts.
"""
import numpy as np, json
from lib import KA, CT, PT, to_idx, to_str, ioc, col_enc

DS  = [d for d in range(1,26) if np.gcd(d,26)==1]
SRC = ''.join(PT[k] for k in ('pk2','pk3','pk5','pk6','pk7','pk4','pk1'))
OBS = {'pk8': ioc(CT['pk8']), 'pk9': ioc(CT['pk9']), 'pk10': ioc(CT['pk10'])}
NS  = {'pk8': 153, 'pk9': 144, 'pk10': 504}
NS_SEED = {'pk8': 8, 'pk9': 9, 'pk10': 10}
NSIM = 4000

def sim(N, m, L, rec, r, W=9):
    off = int(r.integers(0, len(SRC)-N)); pt = SRC[off:off+N]
    if W: pt = col_enc(pt, list(r.permutation(W)))
    p = to_idx(pt, KA).astype(np.int64)
    k = np.zeros(N, dtype=np.int64); k[:L] = r.integers(0, m, L)
    for i in range(L, N):
        k[i] = (k[i-L] + k[i-L+1]) % m if rec=='aca' else (k[i-L] + k[i-1]) % m
    d = int(DS[r.integers(0, len(DS))])
    c = (p + d*k) % 26
    return ioc(to_str(c, KA)), len(set(((d*k) % 26).tolist()))

out = []
print(f"observed IoC: pk8 {OBS['pk8']:.5f} (n=153), pk9 {OBS['pk9']:.5f} (n=144), "
      f"pk10 {OBS['pk10']:.5f} (n=504)\n")
print(f"{'tgt':5s} {'m':>2s} {'L':>2s} {'rec':5s} {'shifts':>6s} {'sim IoC mean':>13s} {'sd':>7s} "
      f"{'z(obs)':>8s} {'P(sim>=obs)':>12s}")
for tag, N in NS.items():
    for m in (3,4,5,6,7,8,10,26):
        for L in (4,6):
            for rec in ('aca',):
                r = np.random.default_rng((NS_SEED[tag]*100000 + m*1000 + L*10 + (0 if rec=='aca' else 1)))
                v = [sim(N, m, L, rec, r) for _ in range(NSIM)]
                io = np.array([a for a,_ in v]); ns = np.mean([b for _,b in v])
                z  = (OBS[tag] - io.mean())/io.std()
                pg = float((io >= OBS[tag]).mean())
                out.append({'target':tag,'m':m,'L':L,'rec':rec,'shifts':round(float(ns),2),
                            'mean':round(float(io.mean()),5),'sd':round(float(io.std()),5),
                            'z':round(float(z),2),'p_ge':pg})
                print(f"{tag:5s} {m:2d} {L:2d} {rec:5s} {ns:6.2f} {io.mean():13.5f} {io.std():7.5f} "
                      f"{z:+8.2f} {pg:12.4f}")
json.dump({'obs':OBS,'rows':out,'nsim':NSIM}, open('results/smallmod_census.json','w'), indent=1)
