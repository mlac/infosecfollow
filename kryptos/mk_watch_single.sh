#!/bin/bash
cd /home/user/infosecfollow/kryptos
while true; do
  n=$(grep -c "^pk10 r0" logs/mk_single_null.log 2>/dev/null)
  if [ "$n" -ge 8 ]; then pkill -9 -f "mk_single.py null"; echo "killed after pk10 r0 complete"; break; fi
  if ! pgrep -f "mk_single.py null" > /dev/null; then echo "finished on its own"; break; fi
  sleep 20
done
