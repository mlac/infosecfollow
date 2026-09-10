#!/bin/bash
cd /home/user/infosecfollow/kryptos
export OMP_NUM_THREADS=1
while pgrep -f "mk_d3.py real" > /dev/null; do sleep 15; done
python3 -u mk_d3.py null 2 > logs/mk_d3_null.log 2>&1
