#!/bin/sh
# infosecfollow refresh + publish to GitHub Pages.
# Scheduled by the LaunchAgent com.infosecfollow.refresh (6am/12pm/4pm/9pm ET).
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"

# The embedded Claude CLI reads its OAuth credential from the login keychain,
# keyed to the account name. Schedulers (cron, launchd) start with a stripped
# environment missing USER/LOGNAME, which makes the CLI report "Not logged in".
# Restore them so the keychain lookup succeeds.
export HOME="${HOME:-$(eval echo "~$(id -un)")}"
export USER="$(id -un)"
export LOGNAME="$USER"

# Prefer the interpreter the project is developed against (a minimal scheduler
# PATH would otherwise pick the stale Apple /usr/bin/python3).
PYTHON="${INFOSECFOLLOW_PYTHON:-}"
if [ -z "$PYTHON" ]; then
    for candidate in "$HOME/.pyenv/shims/python3" /opt/homebrew/bin/python3 \
                     /usr/local/bin/python3 /usr/bin/python3; do
        if [ -x "$candidate" ]; then PYTHON="$candidate"; break; fi
    done
fi

mkdir -p "$DIR/logs"
LOG="$DIR/logs/$(date +%Y-%m-%d).log"
{
    echo "===== run $(date '+%Y-%m-%d %H:%M:%S %Z') ====="
    "$PYTHON" "$DIR/engine/generate.py"

    # Publish: commit the regenerated docs/ and push to GitHub Pages.
    cd "$DIR"
    /usr/bin/git add docs
    if ! /usr/bin/git diff --cached --quiet; then
        /usr/bin/git commit -m "briefing $(date '+%Y-%m-%d %H:%M %Z')"
        /usr/bin/git push origin main
    else
        echo "no site changes to publish"
    fi
} >>"$LOG" 2>&1
