#!/bin/sh
# One briefing cycle: sync the repo, regenerate the site, publish to GitHub Pages.
# Invoked once on container start and at each slot by /app/scheduler.sh, or by
# hand with `docker exec infosecfollow /app/run-briefing.sh`. The repo lives in
# a Docker volume that this script clones on first run, so the NAS host needs
# no git. Secrets come from the container environment (see .env):
# CLAUDE_CODE_OAUTH_TOKEN authenticates the Claude CLI; GITHUB_TOKEN authorises
# the clone/fetch/push; HEARTBEAT_URL (optional) is pinged after every
# successful cycle so a dead-man monitor can alert you when slots stop.
set -eu

REPO_DIR=/data/infosecfollow
REMOTE="${GIT_REMOTE_URL:-https://github.com/mlac/infosecfollow.git}"
LOCK_FILE=/tmp/infosecfollow.lock
STAMP_FILE=/tmp/infosecfollow.last-success   # read by the Docker HEALTHCHECK
GIT_TIMEOUT=120        # seconds for one clone/fetch/push
GENERATE_TIMEOUT=1500  # seconds for generate.py (~60 feeds + three model calls)

echo "===== run $(date '+%Y-%m-%d %H:%M:%S %Z') ====="

# Mutual exclusion: the scheduler, the start-up run, and a manual
# `docker exec ... run-briefing.sh` must never touch the checkout at once.
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "another briefing run is in progress; skipping"
    exit 75
fi

# git reads GIT_AUTHOR_NAME/GIT_AUTHOR_EMAIL itself, so a blank value in .env
# would make every commit fail with "empty ident name": drop blanks and fall back.
[ -n "${GIT_AUTHOR_NAME:-}" ] || unset GIT_AUTHOR_NAME
[ -n "${GIT_AUTHOR_EMAIL:-}" ] || unset GIT_AUTHOR_EMAIL
AUTHOR_NAME="${GIT_AUTHOR_NAME:-infosecfollow-bot}"
AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-infosecfollow@users.noreply.github.com}"

success() {  # record a completed cycle; ping the monitor if one is configured
    touch "$STAMP_FILE"
    [ -n "${HEARTBEAT_URL:-}" ] || return 0
    curl -fsS -m 10 -o /dev/null "$HEARTBEAT_URL" || echo "heartbeat ping failed (ignored)"
}
failure() {  # tell the monitor explicitly (healthchecks.io /fail convention)
    [ -n "${HEARTBEAT_URL:-}" ] || return 0
    curl -fsS -m 10 -o /dev/null "${HEARTBEAT_URL}/fail" || true
}

# Supply the GitHub token for clone/fetch/push without writing it to disk, and
# only for github.com so the credential is never offered to another host. The
# helper runs in a subshell where $GITHUB_TOKEN is read from the environment.
git config --global --unset-all credential.helper 2>/dev/null || true
git config --global credential.https://github.com.helper \
    '!f() { echo username=x-access-token; echo "password=${GITHUB_TOKEN}"; }; f'

# First run: clone into the data volume. A half-initialised volume (a
# directory without .git, e.g. after an interrupted clone) is cleared first,
# which is the manual recovery in OPERATIONS.md 5.4 done automatically.
if [ ! -d "$REPO_DIR/.git" ]; then
    if [ -d "$REPO_DIR" ] && [ -n "$(ls -A "$REPO_DIR" 2>/dev/null)" ]; then
        echo "clearing half-initialised $REPO_DIR"
        find "$REPO_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    fi
    echo "cloning $REMOTE"
    timeout "$GIT_TIMEOUT" git clone "$REMOTE" "$REPO_DIR"
fi
cd "$REPO_DIR"
# --replace-all: one entry, however many earlier runs added (--add appended a
# duplicate line to ~/.gitconfig on every run before this was fixed).
git config --global --replace-all safe.directory "$REPO_DIR"
git remote set-url origin "$REMOTE"   # ensure HTTPS so the token helper applies

# A leftover index.lock can only be stale here: this script holds the run
# lock, so no other git process is using this checkout.
rm -f .git/index.lock

# Start from a clean, current tree. The container is the only writer and always
# pushes, so origin/main is authoritative; this also picks up engine changes you
# push from elsewhere. Every git network call is bounded so a hung connection
# cannot wedge the scheduler.
timeout "$GIT_TIMEOUT" git fetch --quiet origin main
git reset --hard origin/main

# Generate the site (stdlib-only Python; calls the Claude CLI for summaries).
# Bounded so one stuck feed or model call can never block the next slot.
if ! timeout "$GENERATE_TIMEOUT" python3 engine/generate.py; then
    echo "generate.py failed"
    failure
    exit 1
fi

# Publish only if something changed. Note: only docs/ is ever staged, so a
# stray file in the volume can never be committed.
git add docs
if git diff --cached --quiet; then
    echo "no site changes to publish"
    success
    exit 0
fi
git -c user.name="$AUTHOR_NAME" -c user.email="$AUTHOR_EMAIL" \
    commit -m "briefing $(date '+%Y-%m-%d %H:%M %Z')"
# A concurrent push (e.g. you pushing from the Mac at the same moment) makes
# this non-fast-forward; that is harmless because the next run resets to
# origin/main and regenerates. Any other push failure (expired token, network)
# is real: it fails the run so the scheduler logs it and the monitor is told.
if push_out="$(timeout "$GIT_TIMEOUT" git push origin HEAD:main 2>&1)"; then
    echo "published"
    success
elif printf '%s' "$push_out" | grep -qiE 'non-fast-forward|fetch first'; then
    echo "push rejected (concurrent update); next run will regenerate from origin"
    echo "$push_out"
    success
else
    echo "push FAILED:"
    echo "$push_out"
    failure
    exit 1
fi
