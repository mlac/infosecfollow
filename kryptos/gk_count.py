import json, glob, os, sys
runs = []
for f in sorted(glob.glob('results/gromark_L*_mod*.json') + glob.glob('results/gromark_words_L*.json')):
    if 'controls' in f: continue
    for r in json.load(open(f)): r['file'] = os.path.basename(f); runs.append(r)
real_cfg = 0; null_cfg = 0; trials = 0; per = {}
for r in runs:
    nt = len(r['targets'])
    trials += r['executed'] * nt
    for name in r['targets']:
        if '.real.' in name: real_cfg += 1
        else: null_cfg += 1
    k = (r['mod'], r['L'], r.get('tag', '').split('-')[0])
    per[k] = per.get(k, 0) + r['executed'] * nt
print("runs (recurrence x modulus x primer-length x primer-source):", len(runs))
print("REAL search cells  :", real_cfg)
print("NULL search cells  :", null_cfg)
print("total search cells :", real_cfg + null_cfg)
print("total primer trial decryptions: %.3e" % trials)
for k in sorted(per): print("   mod=%d L=%-2d %-14s %.3e trial decryptions" % (k[0], k[1], k[2], per[k]))
