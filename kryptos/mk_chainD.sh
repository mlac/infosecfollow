#!/bin/bash
cd /home/user/infosecfollow/kryptos
export OMP_NUM_THREADS=1
python3 -u mk_two2.py real 0 > logs/mk_two2_real.log 2>&1
python3 -u mk_two2.py null 2 > logs/mk_two2_null.log 2>&1
