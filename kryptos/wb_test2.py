import sys, numpy as np; sys.path.insert(0,'.')
from lib import KA, CT, PT, qscore
import wb_core as W
alpha=KA
words, lp = W.load_vocab(3,16)
trie = W.build_trie(words, lp, alpha)
QGM = W.qg_matrix(alpha)
truept = PT['pk1']; truekey = 'PROVENANCE'*20
truekey = truekey[:len(truept)]
o = W.objective(truept, truekey, trie, QGM, alpha)
print('TRUE  qg/l=%.4f  ptlp=%.1f keylp=%.1f obj=%.4f' % (o['qg_per'],o['pt_lp'],o['key_lp'],o['obj']))
print('  seg pt :', ' '.join(o['seg_pt'])[:160])
print('  seg key:', ' '.join(o['seg_key'])[:160])
print('  qscore(pt) =', qscore(truept))
# THE-spam comparison
spam='THE'*64; spam=spam[:len(truept)]
o2 = W.objective(spam, truekey, trie, QGM, alpha)
print('SPAM  qg/l=%.4f obj=%.4f' % (o2['qg_per'], o2['obj']))
