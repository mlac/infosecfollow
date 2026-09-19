"""Was the claim's OWN 'above the matched null ceiling' event even improbable?
The claim's numbers (results/manufactured_keys.json, MA_single_word):
  real  pk9 : max over  8 per-config grid maxima = 0.06313  (mean 0.05909)
  null  pk9 : max over 16 per-config grid maxima = 0.06070  (mean 0.05774)  [2 shuffles x 8 cfg]
The comparison is max-of-8 vs max-of-16 of the SAME kind of statistic. Under H0 the 24
per-config maxima are exchangeable, so P(the 8 real ones contain the overall maximum) = 8/24.
No modelling assumption is needed for this -- it is a pure rank computation.
"""
import json, numpy as np
from math import comb
out={}
nR,nN=8,16
out['claim_reported']={'real_max_over_8_configs':0.06313,'real_mean':0.05909,
 'null_max_over_16_configs':0.06070,'null_mean':0.05774,'null_shuffles':2}
out['exact_rank_test']={
 'statement':'Under H0 (pk9 exchangeable with its own shuffles) the 24 per-config grid '
             'maxima are exchangeable; the event "real max > null max" is exactly the event '
             '"the global maximum falls in the real block".',
 'P_real_block_holds_the_max': round(nR/(nR+nN),4),
 'interpretation':'The claim\'s headline "above the matched null ceiling" is an event with '
                  'null probability 1/3. It is not evidence of anything.'}
# generalisation: with the real block of 8 and null block of 16, P(max of real >= k-th null)
out['why_the_ceiling_is_underpowered']={
 'null_draws':16,
 'max_of_16_estimates_percentile': round(16/17,4),
 'note':'A max over 16 draws is a noisy estimate of the ~94th percentile of the per-config '
        'distribution. Calling it a "ceiling" and then testing a max over 8 fresh draws '
        'against it inflates the false-positive rate to ~1/3, not 0.05.'}
# the in-cell z is the wrong z
out['the_reported_z_is_a_within_cell_z']={
 'reported':8.1,
 'what_it_measures':'(max - mean)/sd over the ~30k nine-letter words inside ONE cell '
   '(pk9, KA/AZ/sub, revtrunc14, a=9).',
 'what_the_search_actually_was':'8 alphabet/mode configs x 696 constructions per config = '
   '5568 cells per target, 3 targets = 16704 cells; 100,169,664 word-hypotheses per target.',
 'why_it_cannot_be_a_search_z':'A within-cell z conditions on the winning cell having been '
   'chosen, which is exactly the selection being tested. It also assumes the ~30k word scores '
   'inside a cell are the reference set for a statistic that was maximised over 16704 cells.'}
json.dump(out, open('results/adm_ceiling.json','w'), indent=1)
print(json.dumps(out, indent=1))
