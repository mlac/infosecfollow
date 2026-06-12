#!/bin/sh
# infosecfollow daily refresh + publish to GitHub Pages. Suitable for cron:
#   30 7 * * *  /Users/mlac/AI_Projects/infosecfollow/run_daily.sh
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"

# Prefer the interpreter the project is developed against (cron's PATH would
# otherwise pick the stale Apple /usr/bin/python3).
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
    "$PYTHON" "$DIR/engine/generate.py"

    # Publish: commit the regenerated docs/ and push to GitHub Pages.
    cd "$DIR"
    /usr/bin/git add docs
    if ! /usr/bin/git diff --cached --quiet; then
        /usr/bin/git commit -m "daily briefing $(date +%Y-%m-%d)"
        /usr/bin/git push origin main
    else
        echo "no site changes to publish"
    fi
} >>"$LOG" 2>&1
