#!/bin/sh
cd /home/user/infosecfollow/kryptos
for r in 0 1 3 2; do
  OMP_NUM_THREADS=1 GK_NULLS=1 GK_CLS=pk10 python3 -u gk_sweep.py enum 8 10 $r
done
