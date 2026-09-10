#!/bin/bash
cd /home/user/infosecfollow/kryptos
export OMP_NUM_THREADS=1
while pgrep -f "mk_two.py null" > /dev/null; do sleep 15; done
sleep 20
while pgrep -f "mk_cat.py real" > /dev/null; do sleep 15; done
python3 -u mk_cat.py null 2 > logs/mk_cat_null.log 2>&1
