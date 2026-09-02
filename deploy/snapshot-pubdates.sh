#!/bin/sh
# One feed-pubdate snapshot: run the sampler, then publish logs/ to the
# feed-pubdates-data branch WITHOUT touching the shared checkout.
#
# Runs INSIDE the infosecfollow container (shares /data/infosecfollow with
# run-briefing.sh). Invoke from the NAS host, e.g. via DSM Task Scheduler:
#
#   /usr/local/bin/docker exec infosecfollow sh /data/infosecfollow/deploy/snapshot-pubdates.sh
#
# Safe against the briefing pipeline by construction:
# - The snapshot commit is built with a PRIVATE index (GIT_INDEX_FILE) and
#   git commit-tree, then pushed by sha. HEAD, the real index, and the working
#   tree are never modified, so run-briefing.sh's `git reset --hard origin/main`
#   never sees logs/ as tracked (they stay ignored/untracked and accumulate),
#   and a briefing run can never sweep snapshot files into a main commit —
#   even if the two run at the same moment.
# - Exit status is non-zero if EITHER the sampler or the push failed (the
#   sampler's status is captured explicitly; `tee` would otherwise mask it),
#   so a scheduler can detect failure.

cd /data/infosecfollow && [ -d .git ] || exit 1   # never touch an uncloned volume
mkdir -p logs

rc_file=$(mktemp)
{
    echo "=== pubdate snapshot $(date -u "+%Y-%m-%dT%H:%M:%SZ") ==="
    python3 engine/feed_pubdates.py 2>&1
    echo $? > "$rc_file"
    echo "sampler exit code: $(cat "$rc_file")"
    wc -l logs/feed_pubdates.jsonl logs/feed_pubdates_runs.jsonl 2>&1
} | tee logs/pubdate_report.txt
sampler_rc=$(cat "$rc_file" 2>/dev/null || echo 1)
rm -f "$rc_file"

export GIT_INDEX_FILE=/data/infosecfollow/.git/pubdate-index
base=$(git rev-parse origin/main)
git read-tree "$base"
for f in logs/pubdate_report.txt logs/feed_pubdates.jsonl logs/feed_pubdates_runs.jsonl; do
    [ -f "$f" ] && git add -f "$f"
done
tree=$(git write-tree)
c=$(git -c user.name=infosecfollow-bot \
      -c user.email=infosecfollow@users.noreply.github.com \
      commit-tree "$tree" -p "$base" -m "pubdate snapshot $(date -u "+%Y-%m-%d %H:%M")")
unset GIT_INDEX_FILE
rm -f /data/infosecfollow/.git/pubdate-index

push_rc=1
if [ -n "$c" ]; then
    git push -f origin "$c":refs/heads/feed-pubdates-data
    push_rc=$?
fi
echo "push exit code: $push_rc"
[ "$sampler_rc" -eq 0 ] && [ "$push_rc" -eq 0 ]
