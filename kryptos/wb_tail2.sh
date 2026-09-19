#!/bin/bash
cd /home/user/infosecfollow/kryptos; export OMP_NUM_THREADS=1
while kill -0 13021 2>/dev/null; do sleep 15; done
python3 -u wb_run_null89.py > logs/wb_null89.log 2>&1
