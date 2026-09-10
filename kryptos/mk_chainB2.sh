#!/bin/bash
cd /home/user/infosecfollow/kryptos
export OMP_NUM_THREADS=1
while pgrep -f "mk_cat.py real" > /dev/null; do sleep 10; done
python3 -u mk_cat.py null 1 > logs/mk_cat_null.log 2>&1
