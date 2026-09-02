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
#
# Stopping: SIGTERM (docker stop / compose down) sets a flag; an in-flight
# briefing is allowed to finish (compose grants stop_grace_period, sized to
# the longest possible run; a NAS reboot's own service timeout may be shorter)
# and no new one starts. Runs execute in the background and are waited on, so
# the signal is handled promptly rather than after the current sleep.
set -u

WEEKDAY_SLOTS="07:02 10:02 13:32 19:32"
WEEKEND_SLOTS="08:02 19:32"

echo "infosecfollow scheduler up $(date '+%Y-%m-%d %H:%M:%S %Z'); weekday slots $WEEKDAY_SLOTS, weekend slots $WEEKEND_SLOTS"

stopping=0
trap 'stopping=1; echo "stop requested"' TERM INT

run_briefing() {  # $1 = label for the log
    /app/run-briefing.sh &
    child=$!
    rc=""
    while [ -z "$rc" ]; do
        wait "$child"
        w=$?
        # A trapped signal interrupts `wait` while the child is still running;
        # keep waiting so the in-flight run completes before we exit.
        if kill -0 "$child" 2>/dev/null; then
            continue
        fi
        rc=$w
    done
    [ "$rc" -eq 0 ] || echo "$1 failed with status $rc (continuing)"
}

last="$(date +%H:%M)"   # suppress an immediate repeat if we started on a slot
run_briefing "initial run"

while [ "$stopping" -eq 0 ]; do
    slot="$(date +%H:%M)"
    case "$(date +%u)" in            # 1=Mon .. 7=Sun
        6|7) slots="$WEEKEND_SLOTS" ;;
        *)   slots="$WEEKDAY_SLOTS" ;;
    esac
    case " $slots " in
        *" $slot "*)
            if [ "$slot" != "$last" ]; then
                last="$slot"
                run_briefing "run at $slot"
            fi ;;
    esac
    [ "$stopping" -eq 0 ] || break
    sleep 30 &
    wait $!
done
echo "infosecfollow scheduler stopped $(date '+%Y-%m-%d %H:%M:%S %Z')"
