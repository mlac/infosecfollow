"""Multiple-testing / capacity arithmetic for the dual-beam kmin>=8 cell."""
import json, numpy as np, math
d=json.load(open('results/word_beam_pk10.json'))
cap=d['capacity']
print('n=504, log10(26^n)=',cap['log10_26^n'])
for k in ('len>=3','len>=8','len>=10'):
    v=cap['vocab'][k]; print(f"  {k}: {v['words']} words, log10 a_n={v['log10_a_n']}")
print('expected (pt,key) pairs consistent with a random 504-letter ct, pt vocab len>=3:')
print('  key len>=8 :', cap['expected_dual_solutions_log10_ptfull']['len>=8'], 'log10')
print('  key len>=10:', cap['expected_dual_solutions_log10_ptfull']['len>=10'], 'log10')
# hypotheses actually evaluated
print()
print('EXECUTED beam runs claimed:', d['executed_beam_runs'], 'wall_sec', d['wall_clock_seconds'])
