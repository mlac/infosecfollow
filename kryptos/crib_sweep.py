"""Full crib sweep, vectorised.

For a key structure k[i] = sum_f u_f[i mod p_f] and a set of crib POSITIONS, consistency of the
derived keystream K is equivalent to R.K = 0 (mod 26), where R is the left null space of the
incidence matrix. Z26 = GF(2) x GF(13) by CRT, so compute R over each field. Precompute R once
per (structure, positions) and every crib in the corpus is then a single matrix product.
False-positive probability per structure = 2^-r2 * 13^-r13.
"""
import numpy as np, itertools, json, sys
from lib import KA, AZ, CT, PT

def nullspace_gf(M, q):
    """basis (rows) of {v : v @ M = 0} over GF(q); M is (rows x cols) int array"""
    M = np.array(M, dtype=np.int64) % q
    r, c = M.shape
    A = np.concatenate([M, np.eye(r, dtype=np.int64)], axis=1) % q
    piv = 0
    for col in range(c):
        p = next((i for i in range(piv, r) if A[i, col] % q), None)
        if p is None: continue
        A[[piv, p]] = A[[p, piv]]
        A[piv] = (A[piv] * pow(int(A[piv, col]), q-2, q)) % q
        for i in range(r):
            if i != piv and A[i, col] % q:
                A[i] = (A[i] - A[i, col] * A[piv]) % q
        piv += 1
        if piv == r: break
    return A[piv:, c:] % q          # rows whose M-part is zero

def structure_matrix(positions, periods):
    tot = 0; offs = []
    for p in periods: offs.append(tot); tot += p
    A = np.zeros((len(positions), tot), dtype=np.int64)
    for i, pos in enumerate(positions):
        for f, p in enumerate(periods): A[i, offs[f] + (pos % p)] += 1
    return A

def make_checker(positions, periods):
    A = structure_matrix(positions, periods)
    R2 = nullspace_gf(A, 2); R13 = nullspace_gf(A, 13)
    return R2, R13, R2.shape[0], R13.shape[0]

def build_cribs():
    NUM = ['ONE','TWO','THREE','FOUR','FIVE','SIX','SEVEN','EIGHT','NINE','TEN','ELEVEN','TWELVE',
           'THIRTEEN','FOURTEEN','FIFTEEN','SIXTEEN','SEVENTEEN','EIGHTEEN','NINETEEN','TWENTY',
           'THIRTYONE','THIRTY','FORTY','FIFTY','SIXTY','SEVENTY','EIGHTY','NINETY','AHUNDRED',
           'TWENTYONE','TWENTYTWO','TWENTYFIVE','TWENTYEIGHT']
    ORD = ['FIRST','SECOND','THIRD','FOURTH','FIFTH','SIXTH','SEVENTH','EIGHTH','NINTH','TENTH',
           'ELEVENTH','TWELFTH','THIRTEENTH','FOURTEENTH','FIFTEENTH','TWENTIETH']
    UNIT = ['DAY','DAYS','WEEK','WEEKS','MONTH','MONTHS','YEAR','YEARS','WINTER','WINTERS',
            'SUMMER','SUMMERS','MORNING','MORNINGS','NIGHT','NIGHTS','HOUR','HOURS','SPRINGS']
    CONN = ['IN','INTHE','INTO','LATER','HAVEPASSED','PASSED','SINCE','AFTER','ONANDI','ANDI',
            'INTHEBARN','INTHEWORKSHOP','ATTHEFORGE','HOMEAGAIN','GONE','ATTHEBENCH','ONTHEROAD',
            'BEFORE','FROMTHEGATES','WITHTHEWHITESMITH','UNDERHIM','OFWORK','OFSILENCE','OFTHIS']
    C = set()
    for n in NUM:
        for u in UNIT:
            for c in CONN:
                s = n+u+c
                if 18 <= len(s) <= 60: C.add(s)
    for o in ORD:
        for u in ['MONTH','YEAR','WEEK','DAY','WINTER','MONTHI','YEARI']:
            for c in ['IWROTETO','IRETURNED','IHAVE','ITOOK','THEWHITESMITH','IWENTHOME',
                      'IBEGANAGAIN','ANDIAM','IAMHOME','INTHEARCHIVE','OFTHEAPPRENTICESHIP']:
                s = o+u+c
                if 18 <= len(s) <= 60: C.add(s)
    for n in NUM+ORD:
        C.add('INVESTIGATIONLOGITEM'+n)
        C.add('INVESTIGATIONLOGITEMNUMBER'+n)
    LIT = ['THEWHITESMITHSAYS','THEWHITESMITHTOLDME','IRETURNEDTOTHEARCHIVE','IHAVERETURNEDHOME',
      'IHAVECOMEHOMETOTHEARCHIVE','THENEEDLEISINMYPOSSESSION','THELOSTARCHIVEOFPELLEGRIN',
      'IHAVEFOUNDTHELOSTARCHIVE','THEROUTETOTHELOSTARCHIVE','IWENTHOMEASISAIDIWOULD',
      'IAMNOLONGERANAPPRENTICE','THEACCESSIONLOGSAYS','MYHANDSAREMYOWNAGAIN',
      'IHAVEUNRAVELEDTHEKNOT','THEKNOTISUNRAVELED','THETHREADINSCRIBEDWITHLETTERS',
      'TWELVEPRIORARCHIVISTS','IAMTHETHIRTEENTHARCHIVIST','THEWHITESMITHISDEAD',
      'WHENIRETURNEDTOTHEARCHIVE','ITOOKTHENEEDLEANDWENTHOME','THISISMYLASTENTRY',
      'THISISTHELASTENTRYINTHELOG','IHAVEMADEPEACEWITHIT','THEINNERDOOROPENED',
      'BEHINDTHEINNERDOOR','ONMYRETURNTOTHEARCHIVE','IPLACEDTHENEEDLEINTHECASE']
    for s in LIT:
        if len(s) >= 18: C.add(s)
    return sorted(C)

def derive_mat(ct, cribs, alpha, mode, at_end=False):
    ai = {c: i for i, c in enumerate(alpha)}
    Cv = np.array([ai[c] for c in ct]); n = len(ct)
    out = {}
    for m in sorted({len(c) for c in cribs}):
        sub = [c for c in cribs if len(c) == m]
        P = np.array([[ai[ch] for ch in c] for c in sub])
        pos = np.arange(n-m, n) if at_end else np.arange(m)
        Cs = Cv[pos][None, :]
        if mode == 'sub':  K = (Cs - P) % 26
        elif mode == 'add': K = (P - Cs) % 26
        else:               K = (Cs + P) % 26
        out[m] = (sub, pos, K)
    return out
