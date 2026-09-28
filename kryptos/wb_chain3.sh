#!/bin/bash
cd /home/user/infosecfollow/kryptos
export OMP_NUM_THREADS=1
while pgrep -f "wb_run_periodic.py real" >/dev/null; do sleep 20; done
python3 -u wb_run_az.py > logs/wb_az.log 2>&1
