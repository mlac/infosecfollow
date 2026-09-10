import sys,json; sys.path.insert(0,'.')
import numpy as np
CLAIM=0.06799
V=json.load(open('results/qk_manufactured_keys_verify.json'))
V['claim_under_test']={'family':'manufactured long keys / concat+interleave (M-C/M-D)',
 'target':'pk9 (n=144)','cfg':'KA/KA/add','kind':'D (interleave)','a':10,'b':7,
 'key':'GABRIELSEN|DENHOLM (17 letters)','statistic':'IoC of full decrypt','value':CLAIM,
 'family_flag':'above_matched_ceiling: C=true, D=true (mk_cat / manufactured_keys.json)'}
V['reproduction']=json.load(open('results/qk_repro.json'))
for k in V['reproduction']: V['reproduction'][k].pop('pt',None) if False else None
V['degeneracy']=json.load(open('results/qk_degeneracy.json'))
V['positive_control_corrected']=json.load(open('results/qk_pc2.json'))
V['truth_rank_in_cell']=json.load(open('results/qk_truthrank.json'))
V['void_run_note']=('An earlier power/PC attempt (results/qk_relabel_control.json, logs/qk_pc.log, '
 'logs/qk_power.log) used W2="ANNEALS", which is NOT in words.txt, so non-recovery there was '
 'guaranteed by construction and those three runs are VOID.  qk_pc2 repeats them with FURNACE.')
V['verdict']={
 'refuted':True,
 'why':[
  '1. REPRODUCES EXACTLY but is not a solution: the cell re-runs to IoC 0.06799 with the same '
  'words; the decrypt is degenerate (one letter = 20.1% of 144, English mean 13.8%) and scores '
  '-7.48 log10/letter on quadgrams (English -4.30, random -8.23).',
  '2. ROUND-TRIP IS VACUOUS: re-encrypting the decrypt under the same keystream returns pk9 '
  'character for character, but that is an algebraic identity of the modular peel, true for all '
  '3.8e8 word pairs in this cell, so it carries zero evidence.',
  '3. THE NULL WAS STRATIFIED AFTER THE FACT: the family compared per-KIND maxima (real D 0.06799 '
  'vs null D 0.06391) although the search selects over kind as well. In the family OWN 1-shuffle '
  'null file the global maximum is 0.06896 (pk9, CR, KA/AZ/sub, 10/9, MANTZOUKAS|INCIPIENT) -- '
  'higher than the real global maximum 0.06799. Same failure mode as the prior affine z=+4.91.',
  '4. REBUILT MATCHED NULL (mine, 14+14 draws x the identical 1200-cell pk9 search): shuffle '
  'draw-max mean 0.06796 sd 0.00168 -> z=+0.02; relabel (monoalphabetic re-labelling, which '
  'preserves n, the letter multiset, ct IoC 0.04448 and every positional coincidence) draw-max '
  'mean 0.06814 sd 0.00135 -> z=-0.11. 7 of 14 draws reach or beat the claim in BOTH nulls; '
  'empirical p = 0.53. The null covers only pk9, i.e. 1/3 of the real search, so it is conservative.',
  '5. DERIVED NULL on real out-of-family ciphertexts (PK3 period-40 product key, PK7 Hill 3x3, '
  'truncated to n=144/153; PK6 excluded as contaminated): 48 runs, max 0.06803 >= the claim.',
  '6. MULTIPLE TESTING: the reported number is the maximum of 3600 cells x 200x200 joint pairs = '
  '1.44e8 IoC evaluations (plus 2.0e8 decoupled word scorings), selected over 36 run maxima. The '
  'expected maximum of 12 pk9 run maxima under the matched null is 0.0680-0.0681; the observed '
  '0.06799 is AT or BELOW that expectation. Nothing survives correction.',
  '7. NO DETECTION POWER AT THIS LEVEL: with in-dictionary words the identical search recovers a '
  'genuine interleave instance in exactly the claimed cell (a=10,b=7,D,KA/KA/add,n=144) only when '
  'the plaintext IoC is high -- RECOVERED at pt IoC 0.0779 (global argmax ALCHEMISTS|FURNACE, '
  'rank 1), FAILED at 0.0692 and at 0.0602, where chance maxima 0.0700/0.0693 beat the truth. '
  'The claimed 0.06799 sits below the detection floor of its own search.',
  '8. RELABEL NULL VALIDATED: relabelling the recoverable instance destroys it (0.07789 -> 0.06886, '
  'wrong words), so the relabel draws are genuine signal-free draws that keep the real ceiling.'],
 'tier':'Tier 3 screen -- the specific claimed keys are dead; the FAMILY REMAINS OPEN, and for '
        'n=144/153 the concat/interleave solver is demonstrably underpowered (it cannot see a true '
        'instance whose plaintext IoC is below ~0.070), so the negative is not an exhaustion.',
 'recomputed_z':'shuffle-null z=+0.02, relabel-null z=-0.11, empirical p=0.53 (7/14 draws >= claim in each)'}
json.dump(V,open('results/qk_manufactured_keys_verify.json','w'),indent=1)
print(json.dumps(V['verdict'],indent=1))
print('NULL SUMMARY', {k:(V[k]['draw_max_mean'],V[k]['draw_max_sd'],V[k]['draws_at_or_above_claim'],V[k]['draws']) for k in ('my_null_shuffle','my_null_relabel')})
