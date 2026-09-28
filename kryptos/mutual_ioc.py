"""Transposition-invariant SOLVER for a periodic key: align the p column histograms by shift to
maximise pooled IoC. Needs no plaintext alphabet, no quadgram model, and survives an inner
columnar. Section 6's period sweep was quadgram-optimised, which is neither.
Batched over many texts at once so the matched null can be large."""
import numpy as np, json, sys
from lib import *

def hists(M, p):
    """M: (B,n) int array -> (B,p,26) column histograms"""
    B, n = M.shape
    out = np.zeros((B, p, 26))
    for r in range(p):
        S = M[:, r::p]
        for x in range(26):
            out[:, r, x] = (S == x).sum(1)
    return out

def align(H, restarts, rng, iters=60):
    """H: (B,p,26). Coordinate ascent on pooled IoC, vectorised over B. Returns (B,) best IoC."""
    B, p, _ = H.shape
    N = H[0].sum()
    best = np.zeros(B)
    bshift = np.zeros((B, p), dtype=int)
    idx = (np.arange(26)[None, :] + np.arange(26)[:, None]) % 26      # roll table
    for _ in range(restarts):
        s = rng.integers(0, 26, (B, p)); s[:, 0] = 0
        Hs = np.take_along_axis(H, idx[s], axis=2)                    # rolled by -s
        for _ in range(iters):
            changed = False
            pooled = Hs.sum(1)
            for r in range(p):
                rest = pooled - Hs[:, r]
                # score all 26 shifts of column r against `rest`
                cand = np.take_along_axis(H[:, r][:, None, :].repeat(26, 1), idx[None].repeat(B, 0), axis=2)
                sc = np.einsum('bsx,bx->bs', cand, rest)
                v = sc.argmax(1)
                if not np.array_equal(v, s[:, r]):
                    changed = True
                    s[:, r] = v
                    Hs[:, r] = cand[np.arange(B), v]
                    pooled = rest + Hs[:, r]
            if not changed: break
        tot = Hs.sum(1)
        v = (tot*(tot-1)).sum(1)/(N*(N-1))
        upd = v > best
        best = np.where(upd, v, best); bshift[upd] = s[upd]
    return best, bshift

def run(tag, ps, nshuf, restarts, alpha=KA, seed=5):
    rng = np.random.default_rng(seed)
    ct = CT[tag]; n = len(ct)
    C = to_idx(ct, alpha).astype(int)[None, :]
    SH = np.array([to_idx(''.join(rng.permutation(list(ct))), alpha) for _ in range(nshuf)], dtype=int)
    rows = []
    for p in ps:
        if n//p < 6: continue
        o, ks = align(hists(C, p), restarts, rng)
        nv, _ = align(hists(SH, p), restarts, rng)
        rows.append({'p': p, 'obs': round(float(o[0]), 5), 'null_mean': round(float(nv.mean()), 5),
                     'null_max': round(float(nv.max()), 5), 'null_sd': round(float(nv.std()), 5),
                     'z': round(float((o[0]-nv.mean())/nv.std()), 2),
                     'above': bool(o[0] > nv.max()), 'shifts': ks[0].tolist()})
        print(f"  {tag} p={p:2d}: obs {o[0]:.4f}  null mean {nv.mean():.4f} max {nv.max():.4f} "
              f"z={(o[0]-nv.mean())/nv.std():+5.2f} {'<== ABOVE CEILING' if o[0]>nv.max() else ''}", flush=True)
    return rows

if __name__ == '__main__':
    tag = sys.argv[1]; NS = int(sys.argv[2]); RS = int(sys.argv[3])
    out = {}
    for an, al in (('KA', KA), ('AZ', AZ)):
        print(f"--- {tag} alphabet {an} (null = {NS} letter-shuffles, {RS} restarts each) ---")
        out[an] = run(tag, range(2, 25), NS, RS, al)
    json.dump(out, open(f'results/mutualioc_{tag}.json', 'w'), indent=1)
    allz = [r['z'] for a in out.values() for r in a]
    ab = [(a, r['p'], r['obs'], r['null_max']) for a, v in out.items() for r in v if r['above']]
    print(f"\n{tag}: {len(allz)} period/alphabet cells. max z {max(allz):+.2f}. above ceiling: {ab}")
