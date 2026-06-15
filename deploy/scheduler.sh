#!/bin/sh
# Minimal, dependency-free scheduler. Replaces supercronic, which crashed as PID 1
# ("Failed to fork exec") and put the container into a restart loop. Runs one
# briefing on start, then fires at 6:02 / 12:02 / 16:02 / 21:02 in the container's
# $TZ (set to America/New_York in docker-compose.yml). Polls every 30s so it can't
# miss a slot; the `last` guard prevents a double-fire within the same minute.
set -u

echo "infosecfollow scheduler up $(date '+%Y-%m-%d %H:%M:%S %Z'); slots 06:02 12:02 16:02 21:02"

/app/run-briefing.sh || echo "initial run failed (continuing)"
last="$(date +%H:%M)"   # suppress an immediate repeat if we started on a slot

while true; do
    slot="$(date +%H:%M)"
    case "$slot" in
        06:02|12:02|16:02|21:02)
            if [ "$slot" != "$last" ]; then
                last="$slot"
                /app/run-briefing.sh || echo "run at $slot failed (continuing)"
            fi
            ;;
    esac
    sleep 30
done
