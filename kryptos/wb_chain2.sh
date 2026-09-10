#!/bin/bash
cd /home/user/infosecfollow/kryptos
export OMP_NUM_THREADS=1
while pgrep -f "wb_run_null.py 10" >/dev/null; do sleep 20; done
python3 -u wb_run_null.py 8 20 > logs/wb_null8.log 2>&1
