#!/bin/sh
# Minimal, dependency-free scheduler. Replaces supercronic, which crashed as PID 1
# ("Failed to fork exec") and put the container into a restart loop. Runs one
# briefing on start, then fires just AFTER each of the day's publish waves
# (feed publish-time analysis, 2026-07): overnight + Europe + local-morning
# (04:00-07:00), US morning peak (08:00-10:00), midday (12:00-13:30), and the
# evening wave (17:00-19:30). Weekends carry ~6% of feed volume, so only a
# morning and an evening slot run. All times are the container's $TZ (set to
# America/New_York in docker-compose.yml). Polls every 30s so it can't miss a
# slot; the `last` guard prevents a double-fire within the same minute.
set -u

echo "infosecfollow scheduler up $(date '+%Y-%m-%d %H:%M:%S %Z'); weekday slots 07:02 10:02 13:32 19:32, weekend slots 08:02 19:32"

/app/run-briefing.sh || echo "initial run failed (continuing)"
last="$(date +%H:%M)"   # suppress an immediate repeat if we started on a slot

while true; do
    slot="$(date +%H:%M)"
    hit=0
    case "$(date +%u)" in            # 1=Mon .. 7=Sun
        [67])
            case "$slot" in
                08:02|19:32) hit=1 ;;
            esac
            ;;
        *)
            case "$slot" in
                07:02|10:02|13:32|19:32) hit=1 ;;
            esac
            ;;
    esac
    if [ "$hit" = 1 ] && [ "$slot" != "$last" ]; then
        last="$slot"
        /app/run-briefing.sh || echo "run at $slot failed (continuing)"
    fi
    sleep 30
done
