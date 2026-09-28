"""Shared helpers for the Gromark / running-key primer family (frontier item 4)."""
import sys, os, subprocess, random
sys.path.insert(0, '/home/user/infosecfollow/kryptos')
from lib import KA, AZ, KAI, AZI, CT, PT, col_enc, ioc

RECS = {0: 'aca', 1: 'lag1', 2: 'fib', 3: 'subaca'}
KERNEL = '/home/user/infosecfollow/kryptos/gk_kernel'

def keystream(primer, n, rec, mod):
    L = len(primer); k = list(primer)
    for i in range(L, n):
        if   rec == 0: v = k[i-L] + k[i-L+1]
        elif rec == 1: v = k[i-L] + k[i-1]
        elif rec == 2: v = k[i-1] + k[i-2]
        else:          v = k[i-L] - k[i-L+1]
        k.append(v % mod)
    return k[:n]

def idx(s, alpha):
    ai = {c: i for i, c in enumerate(alpha)}
    return [ai[c] for c in s]

def mixalpha(seed):
    r = random.Random(seed); a = list(range(26)); r.shuffle(a); return a

def make_syn(pt, primer, rec, mod, mix, alpha=AZ, form='A', enc_sign=+1, perm=None):
    """form 'A': C = MIX(P) + k   (mix before shift; shift-IoC attackable, any MIX)
       form 'B': C = MIX[(P + k)] (true ACA Gromark; class-IoC attackable only)"""
    txt = col_enc(pt, perm) if perm else pt
    n = len(txt)
    k = keystream(primer, n, rec, mod)
    p = idx(txt, alpha)
    out = []
    for i in range(n):
        if form == 'A': out.append((mix[p[i]] + enc_sign * k[i]) % 26)
        else:           out.append(mix[(p[i] + enc_sign * k[i]) % 26])
    return ''.join(alpha[v] for v in out)

def shuffled(s, seed):
    r = random.Random(seed); l = list(s); r.shuffle(l); return ''.join(l)

def target(name, mode, sign, seq):
    return "TARGET %s %d %d %d %s\n" % (name, mode, sign, len(seq), ' '.join(map(str, seq)))

def run(spec_text, path, timeout=None, quiet=True):
    open(path, 'w').write(spec_text)
    r = subprocess.run([KERNEL, path], capture_output=True, text=True, timeout=timeout)
    return parse(r.stdout)

def parse(out):
    res = {'executed': 0, 'targets': {}}
    cur = None
    for ln in out.splitlines():
        f = ln.split()
        if not f: continue
        if f[0] == 'EXECUTED': res['executed'] = int(f[1])
        elif f[0] == 'TARGET':
            cur = {'name': f[1]}
            for kv in f[2:]:
                a, b = kv.split('=')
                cur[a] = float(b) if '.' in b else int(b)
            cur['top'] = []
            res['targets'][f[1]] = cur
        elif f[0] == 'TOP':
            cur['top'].append({'rank': int(f[1]), 'score': float(f[2]),
                               'primer': [int(x) for x in f[3:]]})
    return res

def header(mod, L, nmax, rec, topk=8, enum=1, primers=None):
    h = "MOD %d\nL %d\nNMAX %d\nREC %d\nTOPK %d\nENUM %d\n" % (mod, L, nmax, rec, topk, enum)
    if primers is not None:
        h += "PRIMERS %d\n" % len(primers)
        h += '\n'.join(' '.join(map(str, p)) for p in primers) + '\n'
    return h
