#!/bin/bash
cd /home/user/infosecfollow/kryptos
export OMP_NUM_THREADS=1
# wait for the dual-real job to finish, then run the periodic nulls
while pgrep -f "wb_run_real.py" >/dev/null; do sleep 20; done
python3 -u wb_run_periodic.py null 20 > logs/wb_per_null.log 2>&1
