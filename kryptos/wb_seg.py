import sys; sys.path.insert(0,'.')
from lib import PT
ws=[w for w in open('words.txt').read().split() if 3<=len(w)<=16]
S=set(ws)
def seg(t):
    n=len(t); dp=[False]*(n+1); bp=[None]*(n+1); dp[0]=True
    for i in range(1,n+1):
        for L in range(3,17):
            if i-L<0: break
            if dp[i-L] and t[i-L:i] in S: dp[i]=True; bp[i]=i-L; break
    return dp,bp
for k,t in PT.items():
    dp,bp=seg(t)
    if dp[len(t)]:
        # reconstruct
        out=[];i=len(t)
        while i>0: out.append(t[bp[i]:i]); i=bp[i]
        print(k,len(t),'FULL', ' '.join(reversed(out))[:120])
    else:
        last=max(i for i in range(len(t)+1) if dp[i])
        print(k,len(t),'FAIL at',last, repr(t[last:last+25]))
