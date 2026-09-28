import json, numpy as np, os, sys
R='results/'
def L(f):
    p=R+f
    return json.load(open(p)) if os.path.exists(p) else []
print('='*78); print('DUAL WORD-CONSTRAINED BEAM (plaintext words x key words), beam=100000')
real=L('wb_dual_real.json')
for r in real:
    print(f"  {r['tag']:18s} kmin={r['kmin']:2d} {r['mode']:4s} obj={r['obj']:8.4f} qg={r['qg']:7.4f}"
          + (f" ptrec={r['pt_recovery']:.3f} keyrec={r['key_recovery']:.3f}" if 'pt_recovery' in r else ''))
for k in (10,8):
    nl=L(f'wb_dual_null_k{k}.json')
    if not nl: continue
    o=np.array([x['obj'] for x in nl]); q=np.array([x['qg'] for x in nl])
    print(f"  NULL kmin={k}  n={len(o)}  obj mean={o.mean():.4f} sd={o.std():.4f} max={o.max():.4f}"
          f" | qg mean={q.mean():.4f} sd={q.std():.4f} max={q.max():.4f}")
    for r in real:
        if r['tag']=='PK10' and r['kmin']==k and r['mode']=='add':
            z=(r['obj']-o.mean())/o.std()
            print(f"    -> PK10 kmin={k} add obj={r['obj']:.4f}  z={z:+.2f}  above_null_max={r['obj']>o.max()}")
print(); print('='*78); print('PERIODIC FREE KEY + word-constrained plaintext, beam=100000, L=25..63')
pr=L('wb_periodic_real.json'); pn=L('wb_periodic_null.json')
for tag in ('PC','PK10','PK8','PK9'):
    rows=[r for r in pr if r['tag'].startswith(tag)]
    if not rows: continue
    if tag=='PC':
        for r in rows: print(f"  {r['tag']:8s} obj={r['obj']:8.4f} ptrec={r['pt_recovery']}")
        continue
    b=max(rows,key=lambda r:r['obj'])
    print(f"  {tag:5s} best over {len(rows)} (L,mode) cells: L={b['L']} {b['mode']} obj={b['obj']:.4f} qg={b['qg']:.4f}")
    print(f"        key={b.get('key','')}")
    print(f"        pt ={b.get('pt','')[:110]}")
if pn:
    o=np.array([x['obj'] for x in pn]); q=np.array([x['qg'] for x in pn])
    print(f"  NULL periodic n={len(o)} (each = max over the same 16 periods)")
    print(f"        obj mean={o.mean():.4f} sd={o.std():.4f} max={o.max():.4f} | qg mean={q.mean():.4f} max={q.max():.4f}")
    rows=[r for r in pr if r['tag']=='PK10' and r.get('mode')=='add']
    if rows:
        b=max(rows,key=lambda r:r['obj'])
        print(f"        -> PK10 add best obj={b['obj']:.4f} z={(b['obj']-o.mean())/o.std():+.2f} above_null_max={b['obj']>o.max()}")
