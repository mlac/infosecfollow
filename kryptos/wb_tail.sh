#!/bin/bash
cd /home/user/infosecfollow/kryptos; export OMP_NUM_THREADS=1
while kill -0 8880 2>/dev/null; do sleep 15; done
python3 -u wb_run_az.py    > logs/wb_az.log    2>&1
python3 -u wb_run_null.py 8 8 > logs/wb_null8.log 2>&1
python3 -u wb_run_power.py > logs/wb_power.log 2>&1
echo TAILDONE
