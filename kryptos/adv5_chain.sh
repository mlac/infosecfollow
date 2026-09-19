#!/bin/bash
cd /home/user/infosecfollow/kryptos; export OMP_NUM_THREADS=1
while pgrep -f "adv5_beaunull.py sub 8" >/dev/null; do sleep 20; done
python3 -u adv5_beaunull.py sub 10 8 > logs/adv5_subnull_k10.log 2>&1
