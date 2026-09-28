#!/bin/bash
cd /home/user/infosecfollow/kryptos
export OMP_NUM_THREADS=1
while pgrep -f "mk_single.py real" > /dev/null; do sleep 15; done
python3 -u mk_single.py null 2 > logs/mk_single_null.log 2>&1
