#!/bin/sh
# One briefing cycle: sync the repo, regenerate the site, publish to GitHub Pages.
# Invoked on container start and by supercronic on the schedule in ./crontab.
# Secrets come from the container environment (see .env): CLAUDE_CODE_OAUTH_TOKEN
# authenticates the Claude CLI; GITHUB_TOKEN authorises the push.
set -eu

REPO_DIR=/data/infosecfollow
cd "$REPO_DIR"

echo "===== run $(date '+%Y-%m-%d %H:%M:%S %Z') ====="

# The repo is bind-mounted from the NAS, so git sees a different owner uid.
git config --global --add safe.directory "$REPO_DIR"
# Supply the GitHub token for fetch/push without writing it to disk. The helper
# runs in a subshell where $GITHUB_TOKEN is read from the environment.
git config --global credential.helper \
    '!f() { echo username=x-access-token; echo "password=${GITHUB_TOKEN}"; }; f'

# Make sure we push over HTTPS (the token helper only applies to https remotes).
if [ -n "${GIT_REMOTE_URL:-}" ]; then
    git remote set-url origin "$GIT_REMOTE_URL"
fi

# Start from a clean, current tree. The container is the only writer and always
# pushes, so origin/main is authoritative; this also picks up engine changes you
# push from elsewhere.
git fetch --quiet origin main
git reset --hard origin/main

# Generate the site (stdlib-only Python; calls the Claude CLI for summaries).
python3 engine/generate.py

# Publish only if something changed.
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
