"""FRONTIER 6, done properly. Design law 4: PK5's key is PK4's PLAINTEXT. The setter says PK9
unlocks PK8. So hypothesise PK8's key = PK9's plaintext (wrapped, since 144 < 153):

    p8[i] = c8[i] - PT9[i mod 144],  and  PT9[i] = c9[i] - K9[i]
 => p8[i] = (c8[i] - c9[i]) + K9[i]   for i < 144

So d = c8 - c9 is PK8's PLAINTEXT enciphered under PK9's own keystream. PK9's plaintext never has
to be known. Attack d with the whole battery. Same construction for every ordered pair and for
PK10 as the outer text.
Note also: a 144-letter key on a 153-letter message has PERIOD 144, which no column test can see
(only 9 columns would hold 2 letters) -- so this hypothesis is invisible to every period scan and
must be attacked through d.
"""
import numpy as np, itertools
from lib import KA, AZ, CT

def derived_texts():
    out = {}
    for x, y in itertools.permutations(['pk8', 'pk9', 'pk10'], 2):
        for an, al in (('KA', KA), ('AZ', AZ)):
            ai = {c: i for i, c in enumerate(al)}
            A = [ai[c] for c in CT[x]]; B = [ai[c] for c in CT[y]]
            n, m = len(A), len(B)
            for rev in (False, True):
                Bv = B[::-1] if rev else B
                for sign in (+1, -1):
                    v = [(A[i] + sign*Bv[i % m]) % 26 for i in range(n)]
                    tag = f"{x}{'-' if sign<0 else '+'}{y}{'R' if rev else ''}_{an}"
                    out[tag] = (''.join(al[t] for t in v), an)
    return out
