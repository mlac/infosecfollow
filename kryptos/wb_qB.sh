#!/bin/bash
cd /home/user/infosecfollow/kryptos; export OMP_NUM_THREADS=1
while pgrep -f "wb_run_real.py" >/dev/null; do sleep 15; done
python3 -u wb_run_periodic.py null 10 20 > logs/wb_per_null_B.log 2>&1
python3 -u wb_run_null.py 8 8 > logs/wb_null8.log 2>&1
