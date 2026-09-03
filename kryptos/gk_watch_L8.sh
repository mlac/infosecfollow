#!/bin/sh
cd /home/user/infosecfollow/kryptos
while ! grep -q synB504 logs/gromark_L8.log; do sleep 15; done
sleep 5
pkill -f "enum 8 10 0,1,2,3"
sleep 2
for r in 0 1 3 2; do
  OMP_NUM_THREADS=1 GK_NULLS=1 GK_CLS=pk10 nice -n 10 python3 -u gk_sweep.py enum 8 10 $r >> logs/gromark_L8_sweep.log 2>&1
done
echo ALLDONE >> logs/gromark_L8_sweep.log
