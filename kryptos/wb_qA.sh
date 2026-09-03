#!/bin/bash
cd /home/user/infosecfollow/kryptos; export OMP_NUM_THREADS=1
while pgrep -f "wb_run_periodic.py real" >/dev/null; do sleep 15; done
python3 -u wb_run_periodic.py null 0 10 > logs/wb_per_null_A.log 2>&1
