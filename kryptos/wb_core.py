"""Word-constrained dual beam search (plaintext words x key words) over a
Vigenere-family stream cipher.  Frontier item 5, PK10.

Model:  cv[i] = f(pv[i], kv[i])  on a 26-letter alphabet ALPHA (KA or AZ).
  'add' : c = p + k   ->  kv = (cv - pv) % 26     (q3enc / Quagmire-III additive)
  'sub' : c = p - k   ->  kv = (pv - cv) % 26     (standard Vigenere decrypt sense)
  'beau': c = k - p   ->  kv = (cv + pv) % 26     (Beaufort)

Both the plaintext stream AND the key stream must be a concatenation of
dictionary words.  State = (position, pt-trie node, key-trie node, quadgram ctx).
Score = sum quadgram(pt) + Wpt*sum logP(pt words) + Wkey*sum logP(key words).
"""
import numpy as np, sys, time
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
from lib import KA, AZ, AZI, load_quadgrams

# ---------------------------------------------------------------- vocabulary
def load_vocab(minL=3, maxL=16, topk=None, path='/home/user/infosecfollow/kryptos/words.txt'):
    """words.txt is in wordfreq rank order.  Returns (words, logprob) with a
    Zipf 1/rank prior over the *retained* vocabulary."""
    ws = open(path).read().split()
    if topk: ws = ws[:topk]
    keep = [(r, w) for r, w in enumerate(ws) if minL <= len(w) <= maxL]
    ranks = np.array([r for r, _ in keep], dtype=np.float64) + 1.0
    words = [w for _, w in keep]
    p = 1.0 / ranks
    p /= p.sum()
    return words, np.log10(p)

# ---------------------------------------------------------------- trie
def build_trie(words, lp, alpha):
    ai = {c: i for i, c in enumerate(alpha)}
    cap = sum(len(w) for w in words) + 1
    CONT = np.full((cap, 26), -1, dtype=np.int32)
    ISEND = np.zeros(cap, dtype=bool)
    ENDLP = np.zeros(cap, dtype=np.float32)
    nn = 1
    for w, l in zip(words, lp):
        cur = 0
        for ch in w:
            j = ai[ch]
            nxt = CONT[cur, j]
            if nxt < 0:
                CONT[cur, j] = nn; nxt = nn; nn += 1
            cur = nxt
        if ISEND[cur]:
            ENDLP[cur] = max(ENDLP[cur], l)   # shouldn't happen (unique words)
        else:
            ISEND[cur] = True; ENDLP[cur] = l
    return CONT[:nn].copy(), ISEND[:nn].copy(), ENDLP[:nn].copy(), nn

# ---------------------------------------------------------------- quadgrams
def qg_matrix(alpha):
    """quadgram table re-indexed into ALPHA-position space, shape (17576, 26)."""
    qg = load_quadgrams().reshape(26, 26, 26, 26)
    pa = np.array([AZI[c] for c in alpha])
    qa = qg[np.ix_(pa, pa, pa, pa)].astype(np.float32)
    return qa.reshape(17576, 26)

# ---------------------------------------------------------------- beam
def keyperm(mode, cv):
    p = np.arange(26)
    if mode == 'add':  return (cv - p) % 26
    if mode == 'sub':  return (p - cv) % 26
    if mode == 'beau': return (cv + p) % 26
    raise ValueError(mode)

def dual_beam(ct, trie, QGM, mode='add', beam=100000, Wpt=1.0, Wkey=1.0,
              free_key=False, verbose=0, keep_paths=True, trie_key=None):
    """ct: array of ALPHA-position ints.  trie: (CONT, ISEND, ENDLP, nn) for the
    PLAINTEXT side; trie_key (default = trie) for the KEY side.
    free_key=True disables the key-side word constraint entirely."""
    CONT, ISEND, ENDLP, NN = trie
    KCONT, KISEND, KENDLP, KNN = trie_key if trie_key is not None else trie
    ROOTCH = CONT[0].copy(); KROOTCH = KCONT[0].copy()
    n = len(ct)
    L26 = np.arange(26, dtype=np.int64)

    ptn = np.zeros(1, dtype=np.int32)
    kyn = np.zeros(1, dtype=np.int32)
    ctx = np.zeros(1, dtype=np.int64)
    sc  = np.zeros(1, dtype=np.float32)
    PATH = np.zeros((1, n), dtype=np.uint8) if keep_paths else None

    t0 = time.time()
    for i in range(n):
        cv = int(ct[i])
        perm = keyperm(mode, cv)
        N = ptn.shape[0]
        ptrow = CONT[ptn]                          # [N,26] continue pt word
        pte   = ISEND[ptn]
        ptres = np.where(pte[:, None], ROOTCH[None, :], np.int32(-1))
        if free_key:
            kyc = np.zeros((N, 26), dtype=np.int32)
            kyr = np.full((N, 26), -1, dtype=np.int32)
            kye = np.zeros(N, dtype=bool)
        else:
            kyc = KCONT[kyn][:, perm]
            kye = KISEND[kyn]
            kyr = np.where(kye[:, None], KROOTCH[perm][None, :], np.int32(-1))
        qgadd = QGM[ctx] if i >= 3 else np.zeros((N, 26), dtype=np.float32)
        base = sc[:, None] + qgadd
        ptbon = (Wpt * ENDLP[ptn])[:, None]
        kybon = (Wkey * KENDLP[kyn])[:, None] if not free_key else 0.0

        cand_pt, cand_ky, cand_sc, cand_par, cand_let = [], [], [], [], []
        for (pa, pb, pbon) in ((ptrow, 0, 0.0), (ptres, 1, ptbon)):
            for (ka, kb, kbon) in ((kyc, 0, 0.0), (kyr, 1, kybon)):
                if free_key and kb == 1: continue
                ok = (pa >= 0) & (ka >= 0)
                idx = np.flatnonzero(ok.ravel())
                if idx.size == 0: continue
                r = idx // 26; c = (idx - r * 26).astype(np.int64)
                cand_pt.append(pa.ravel()[idx])
                cand_ky.append(ka.ravel()[idx])
                cand_sc.append((base + pbon + kbon).ravel()[idx])
                cand_par.append(r)
                cand_let.append(c)
        if not cand_pt:
            raise RuntimeError(f'beam died at position {i}')
        npt = np.concatenate(cand_pt); nky = np.concatenate(cand_ky)
        nsc = np.concatenate(cand_sc); npar = np.concatenate(cand_par)
        nlet = np.concatenate(cand_let)
        nctx = (ctx[npar] % 676) * 26 + nlet

        # dedup on (ptnode, keynode, ctx) keeping best score
        key = (npt.astype(np.int64) * KNN + nky) * 17576 + nctx
        order = np.argsort(-nsc, kind='stable')
        _, first = np.unique(key[order], return_index=True)
        sel = order[first]
        if sel.size > beam:
            part = np.argpartition(-nsc[sel], beam)[:beam]
            sel = sel[part]
        ptn = npt[sel]; kyn = nky[sel]; sc = nsc[sel]
        ctx = nctx[sel]
        par = npar[sel]; let = nlet[sel]
        if keep_paths:
            PATH = PATH[par]
            PATH[:, i] = let.astype(np.uint8)
        if verbose and (i % 50 == 0 or i == n - 1):
            print(f'   pos {i:4d} N={ptn.shape[0]:8d} best={sc.max()/max(i,1):8.4f} '
                  f'{time.time()-t0:6.1f}s', flush=True)
    # final: require plaintext ends on a word boundary
    fin = sc + Wpt * ENDLP[ptn] * ISEND[ptn]
    if not free_key:
        fin = fin + Wkey * KENDLP[kyn] * KISEND[kyn]
    good = np.flatnonzero(ISEND[ptn])
    if good.size == 0: good = np.arange(ptn.shape[0])
    b = good[np.argmax(fin[good])]
    return dict(score=float(fin[b]) / n, raw=float(fin[b]),
                path=(PATH[b].copy() if keep_paths else None),
                nstates=int(ptn.shape[0]), sec=time.time() - t0,
                all_scores=fin[good] / n)

def decode_path(path, ct, mode, alpha):
    pv = np.asarray(path, dtype=np.int64)
    cv = np.asarray(ct, dtype=np.int64)
    if mode == 'add':  kv = (cv - pv) % 26
    elif mode == 'sub': kv = (pv - cv) % 26
    else:              kv = (cv + pv) % 26
    s = lambda a: ''.join(alpha[int(x)] for x in a)
    return s(pv), s(kv)

def best_seg_lp(s, trie, alpha, tail=False):
    """Viterbi best word-segmentation log-prob of string s (sum of word logps).
    Returns (-inf, None) if s cannot be segmented into dictionary words."""
    CONT, ISEND, ENDLP, NN = trie
    ai = {c: i for i, c in enumerate(alpha)}
    n = len(s); NEG = -1e18
    dp = np.full(n + 1, NEG); dp[0] = 0.0; bp = [-1]*(n+1)
    for i in range(n):
        if dp[i] <= NEG/2: continue
        cur = 0
        for j in range(i, n):
            cur = CONT[cur, ai[s[j]]]
            if cur < 0: break
            if ISEND[cur] and dp[i] + ENDLP[cur] > dp[j+1]:
                dp[j+1] = dp[i] + ENDLP[cur]; bp[j+1] = i
    if tail:
        # the final word may be truncated: any prefix of a dictionary word, cost 0
        for i in range(n):
            if dp[i] <= NEG/2: continue
            cur = 0; ok = True
            for j in range(i, n):
                cur = CONT[cur, ai[s[j]]]
                if cur < 0: ok = False; break
            if ok and dp[i] > dp[n]:
                dp[n] = dp[i]; bp[n] = i
    if dp[n] <= NEG/2: return float('-inf'), None
    out = []; i = n
    while i > 0: out.append(s[bp[i]:i]); i = bp[i]
    return float(dp[n]), list(reversed(out))

def objective(pt, key, trie, QGM, alpha, Wpt=1.0, Wkey=1.0, trie_key=None):
    ai = {c: i for i, c in enumerate(alpha)}
    a = np.array([ai[c] for c in pt], dtype=np.int64)
    ctx = a[:-3]*17576 + a[1:-2]*676 + a[2:-1]*26 + a[3:]
    qg = float(QGM.ravel()[ctx].sum())
    lpt, sp = best_seg_lp(pt, trie, alpha)
    lky, sk = best_seg_lp(key, trie_key if trie_key is not None else trie, alpha, tail=True)
    n = len(pt)
    return dict(qg_per=qg/n, pt_lp=lpt, key_lp=lky,
                obj=(qg + Wpt*lpt + Wkey*lky)/n, seg_pt=sp, seg_key=sk)

# ------------------------------------------------ variant 2: periodic free key
def _pfromk(mode, cv, kv):
    if mode == 'add':  return (cv - kv) % 26
    if mode == 'sub':  return (cv + kv) % 26
    return (kv - cv) % 26            # beau: c = k - p

def bigram_tables(alpha):
    """Marginalise the quadgram model down to bigram / unigram log10-probs,
    in ALPHA-position space."""
    qg = load_quadgrams().reshape(26, 26, 26, 26)
    pa = np.array([AZI[c] for c in alpha])
    q = np.power(10.0, qg[np.ix_(pa, pa, pa, pa)])
    bi = q.sum(axis=(0, 3)); bi /= bi.sum()
    uni = bi.sum(axis=0); uni /= uni.sum()
    return np.log10(bi + 1e-12).astype(np.float32), np.log10(uni + 1e-12).astype(np.float32)

def _lookahead(ct, mode, L, BI, UNI):
    """For residue r, LA[r] is a 26x26 table indexed [k_{r-1}, k_r] giving the
    bigram log-prob of every already-determined pair (p_{j-1}, p_j) with
    j%L==r and j>=L; LA0 is the 26-vector unigram term for residue 0."""
    n = len(ct); cv = np.asarray(ct, dtype=np.int64)
    K = np.arange(26)
    LA = []
    for r in range(L):
        js = np.arange(r, n, L)
        js = js[js >= L]                       # pairs whose left member exists
        if r == 0:
            js = js[js >= 1]
        if js.size == 0:
            LA.append(np.zeros((26, 26), dtype=np.float32)); continue
        rprev = (r - 1) % L
        pcur = _pfromk(mode, cv[js][None, :], K[:, None])          # [26, m]
        pprv = _pfromk(mode, cv[js-1][None, :], K[:, None])        # [26, m]
        t = BI[pprv[:, None, :], pcur[None, :, :]].sum(axis=2)     # [kprev, kcur]
        LA.append(t.astype(np.float32))
    # unigram term for the very first residue's own column
    js0 = np.arange(0, n, L); js0 = js0[js0 >= L]
    LA0 = UNI[_pfromk(mode, cv[js0][None, :], K[:, None])].sum(axis=1).astype(np.float32) \
          if js0.size else np.zeros(26, dtype=np.float32)
    return LA, LA0

def periodic_beam(ct, trie, QGM, mode='add', L=27, beam=100000, Wpt=1.0,
                  verbose=0, BI=None, UNI=None):
    """Plaintext must decompose into dictionary words; key is FREE but periodic
    with period L.  Phase 1 (i<L) branches 26 ways pruned by the word trie and
    keeps `beam` candidate key-prefixes; phase 2 (i>=L) is deterministic -- the
    pinned key fixes every remaining plaintext letter, and states die when the
    plaintext stops being word-decomposable.  Only the L-letter key is stored;
    the plaintext is reconstructed from it."""
    CONT, ISEND, ENDLP, NN = trie
    ROOTCH = CONT[0].copy()
    n = len(ct); t0 = time.time()
    ptn = np.zeros(1, dtype=np.int32); ctx = np.zeros(1, dtype=np.int64)
    sc = np.zeros(1, dtype=np.float32); hs = np.zeros(1, dtype=np.float32)
    P1 = np.zeros((1, L), dtype=np.uint8)
    KP = np.zeros((1, L), dtype=np.int64)          # pinned key letters
    LA, LA0 = (None, None)
    if BI is not None:
        LA, LA0 = _lookahead(ct, mode, L, BI, UNI)
    for i in range(min(L, n)):
        N = ptn.shape[0]
        ptrow = CONT[ptn]
        ptres = np.where(ISEND[ptn][:, None], ROOTCH[None, :], np.int32(-1))
        qg = QGM[ctx] if i >= 3 else np.zeros((N, 26), dtype=np.float32)
        base = sc[:, None] + qg
        kcur = keyperm(mode, int(ct[i]))[np.arange(26)]        # k for each pt letter
        if LA is not None:
            if i == 0:
                look = LA0[kcur][None, :] + LA[0][KP[:, (L-1)] , :][:, kcur] * 0.0
            else:
                look = LA[i][KP[:, i-1], :][:, kcur]
        else:
            look = 0.0
        heur = hs[:, None] + (base - sc[:, None]) + look
        cp, cs, ch, cr, cl = [], [], [], [], []
        for (pa, bon) in ((ptrow, 0.0), (ptres, (Wpt*ENDLP[ptn])[:, None])):
            idx = np.flatnonzero((pa >= 0).ravel())
            if idx.size == 0: continue
            r = idx // 26; c = (idx - r*26).astype(np.int64)
            cp.append(pa.ravel()[idx]); cs.append((base + bon).ravel()[idx])
            ch.append((heur + bon).ravel()[idx]); cr.append(r); cl.append(c)
        npt = np.concatenate(cp); nsc = np.concatenate(cs); nhs = np.concatenate(ch)
        npar = np.concatenate(cr); nlet = np.concatenate(cl)
        sel = np.argpartition(-nhs, beam)[:beam] if nhs.size > beam else np.arange(nhs.size)
        ptn = npt[sel]; sc = nsc[sel]; hs = nhs[sel]
        par = npar[sel]; let = nlet[sel]
        ctx = (ctx[par] % 676)*26 + let
        P1 = P1[par]; P1[:, i] = let.astype(np.uint8)
        KP = KP[par]; KP[:, i] = kcur[let]
    KEYS = np.empty((ptn.shape[0], L), dtype=np.int64)
    for r in range(L):
        KEYS[:, r] = keyperm(mode, int(ct[r]))[P1[:, r].astype(np.int64)]
    alive = np.arange(ptn.shape[0])
    for i in range(L, n):
        cv = int(ct[i]); p = _pfromk(mode, cv, KEYS[:, i % L])
        nxt = CONT[ptn, p]
        alt = np.where(ISEND[ptn], ROOTCH[p], np.int32(-1))
        bon = (Wpt*ENDLP[ptn])*(nxt < 0)
        use = np.where(nxt >= 0, nxt, alt)
        keep = np.flatnonzero(use >= 0)
        if keep.size == 0:
            return dict(score=None, dead_at=i, nstates=0, sec=time.time()-t0, key=None)
        qg = QGM.ravel()[ctx*26 + p] if i >= 3 else np.zeros(len(p), dtype=np.float32)
        sc = sc[keep] + qg[keep] + bon[keep]
        ptn = use[keep].astype(np.int32)
        ctx = (ctx[keep] % 676)*26 + p[keep]
        KEYS = KEYS[keep]; alive = alive[keep]
    fin = sc + Wpt*ENDLP[ptn]*ISEND[ptn]
    good = np.flatnonzero(ISEND[ptn])
    if good.size == 0: good = np.arange(ptn.shape[0])
    order = good[np.argsort(-fin[good])]
    b = order[0]
    return dict(score=float(fin[b])/n, key=KEYS[b].copy(), dead_at=None,
                nstates=int(ptn.shape[0]), survivors=int(ptn.shape[0]),
                sec=time.time()-t0,
                top=[(float(fin[j])/n, KEYS[j].copy()) for j in order[:5]])

def periodic_decode(ct, key, mode, L):
    cv = np.asarray(ct, dtype=np.int64)
    kv = np.asarray(key, dtype=np.int64)[np.arange(len(cv)) % L]
    return _pfromk(mode, cv, kv)
