#!/bin/sh
# One briefing cycle: sync the repo, regenerate the site, publish to GitHub Pages.
# Invoked on container start and by supercronic on the schedule in ./crontab.
# The repo lives in a Docker volume that this script clones on first run, so the
# NAS host needs no git. Secrets come from the container environment (see .env):
# CLAUDE_CODE_OAUTH_TOKEN authenticates the Claude CLI; GITHUB_TOKEN authorises
# the clone/fetch/push.
set -eu

REPO_DIR=/data/infosecfollow
REMOTE="${GIT_REMOTE_URL:-https://github.com/mlac/infosecfollow.git}"

echo "===== run $(date '+%Y-%m-%d %H:%M:%S %Z') ====="

# Supply the GitHub token for clone/fetch/push without writing it to disk. The
# helper runs in a subshell where $GITHUB_TOKEN is read from the environment.
git config --global credential.helper \
    '!f() { echo username=x-access-token; echo "password=${GITHUB_TOKEN}"; }; f'

# First run: clone into the data volume. Later runs: the clone already exists.
if [ ! -d "$REPO_DIR/.git" ]; then
    echo "cloning $REMOTE"
    git clone "$REMOTE" "$REPO_DIR"
fi
cd "$REPO_DIR"
git config --global --add safe.directory "$REPO_DIR"
git remote set-url origin "$REMOTE"   # ensure HTTPS so the token helper applies

# Start from a clean, current tree. The container is the only writer and always
# pushes, so origin/main is authoritative; this also picks up engine changes you
# push from elsewhere.
git fetch --quiet origin main
git reset --hard origin/main

# Generate the site (stdlib-only Python; calls the Claude CLI for summaries).
python3 engine/generate.py

# Publish only if something changed. Note: only docs/ is ever staged, so a
# stray file in the volume can never be committed.
git add docs
if git diff --cached --quiet; then
    echo "no site changes to publish"
    exit 0
fi
git -c user.name="${GIT_AUTHOR_NAME:-infosecfollow-bot}" \
    -c user.email="${GIT_AUTHOR_EMAIL:-infosecfollow@users.noreply.github.com}" \
    commit -m "briefing $(date '+%Y-%m-%d %H:%M %Z')"
git push origin HEAD:main
echo "published"
