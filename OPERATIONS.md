# infosecfollow — Operations Runbook

Everything needed to check, fix, and maintain the site from any machine,
with no AI assistant in the loop. Written 2026-07-29.

---

## 1. What runs where

```
┌─────────────────────────┐   git push main    ┌──────────────────────────┐
│ Synology NAS            │ ─────────────────► │ GitHub mlac/infosecfollow │
│ "workbench-nas"         │                    │                          │
│ Tailscale 100.70.40.114 │                    │  push to main triggers   │
│                         │                    │  .github/workflows/       │
│ Docker container        │                    │  deploy-pages.yml         │
│  name: infosecfollow    │                    │      │                   │
│  volume:                │                    │      ▼                   │
│  infosecfollow-data     │                    │  GitHub Pages            │
│  → /data/infosecfollow  │                    │  https://infosecfollow.com│
└─────────────────────────┘                    └──────────────────────────┘
```

- **The container is the publisher.** `deploy/scheduler.sh` (baked into the
  image) fires `/app/run-briefing.sh` at **7:02, 10:02, 13:32, 19:32 ET on
  weekdays** and **8:02, 19:32 ET on weekends**, plus **once immediately
  whenever the container (re)starts**. Slots sit just after the feeds' four
  daily publish waves (per the 2026-07 publish-time analysis). Each run:
  `git reset --hard origin/main` → `python3 engine/generate.py` (fetches ~58
  feeds, calls the Claude CLI to cluster) → commit `docs/` → push to `main`.
- **The site is served by GitHub Pages via Actions**, not directly from the
  branch: every push to `main` runs `deploy-pages.yml`, which uploads `docs/`
  and deploys (3 attempts with backoff). A stale site can therefore be EITHER
  a missing commit (container problem) OR a failed deploy (GitHub problem).
- **The Mac is not in the loop.** `run_daily.sh` + `com.infosecfollow.refresh.plist`
  are the legacy macOS path, replaced by the NAS. Keep the LaunchAgent
  unloaded (`launchctl bootout gui/$UID/com.infosecfollow.refresh`) so the two
  can never double-publish.

Secrets live in **`/volume1/docker/infosecfollow/.env` on the NAS** (the
compose folder — the four build files sit flat in it; never in the repo):
`CLAUDE_CODE_OAUTH_TOKEN` (Claude subscription token, ~1-year life),
`GITHUB_TOKEN` (fine-grained PAT, Contents R/W on mlac/infosecfollow),
`GIT_REMOTE_URL`, `GIT_AUTHOR_NAME/EMAIL`. Field reference:
`deploy/.env.example` in the repo.

---

## 2. The 60-second health check (from any machine)

1. **Is the site current?** Open https://infosecfollow.com — the header shows
   the generation timestamp. Current = no older than the previous slot
   (≤ ~6h during a weekday; the overnight and weekend-midday gaps run ~11h).
2. **Did commits land?** https://github.com/mlac/infosecfollow/commits/main —
   expect a `briefing YYYY-MM-DD HH:MM EDT/EST` commit ~3–5 min after each slot.
3. **Did the deploy succeed?** https://github.com/mlac/infosecfollow/actions —
   the newest "Deploy to GitHub Pages" run should be green.

| Symptom | Meaning | Go to |
|---|---|---|
| No commit for the last slot | Container/NAS/API problem | §4 |
| Commit exists, Actions red | Pages deploy failed | §5.6 |
| Commit exists, Actions green, site stale | Browser/CDN cache | hard-refresh |

---

## 3. Getting into the NAS

### 3a. DSM web UI (always works)
`http://100.70.40.114:5000` (Tailscale must be up on your machine) — or the
NAS's LAN IP from home. Log in as `mlac` (an administrators-group account).
Container Manager = Docker UI; Task Scheduler = cron UI; File Station = files.

### 3b. Restore SSH access from a new machine
Synology only accepts SSH from administrators-group users, and this NAS has
password auth disabled (`Permission denied (publickey)`), so install your key
via DSM once per machine:

1. On the new machine: `ssh-keygen -t ed25519` (accept defaults), then copy
   the single line in `~/.ssh/id_ed25519.pub`.
2. DSM → Control Panel → **Terminal & SNMP** → confirm *Enable SSH service*.
3. DSM → Control Panel → **User & Group → Advanced → Enable user home service**
   (needed for `~/.ssh` to exist).
4. DSM → Task Scheduler → Create → Scheduled Task → **User-defined script**,
   user **root**, then paste (with YOUR key in `KEY=`):
   ```sh
   KEY="ssh-ed25519 AAAA...rest-of-your-public-key... you@machine"
   H=$(readlink -f /var/services/homes/mlac)
   mkdir -p "$H/.ssh"
   grep -qxF "$KEY" "$H/.ssh/authorized_keys" 2>/dev/null \
       || echo "$KEY" >> "$H/.ssh/authorized_keys"
   chown -R mlac:users "$H/.ssh"
   chmod 755 "$H"; chmod 700 "$H/.ssh"; chmod 600 "$H/.ssh/authorized_keys"
   ```
5. Select the task → **Run** → then from your machine:
   `ssh mlac@100.70.40.114` — should log straight in. Delete the task after.

Permissions matter: Synology sshd uses `StrictModes`, so a group-writable
home or `.ssh` silently breaks key auth — the `chmod` lines are not optional.

### 3c. DSM Task Scheduler gotchas (why one-off tasks "do nothing")
- Run as **root** unless you know the user has docker rights.
- The scheduler PATH is minimal: use **`/usr/local/bin/docker`**, never bare
  `docker`.
- Output is invisible by default: Task Scheduler → **Settings** → enable
  *Save output results* to a folder (or per-task email). Do this BEFORE
  debugging anything.

---

## 4. Playbook: a slot was missed / site is stale

Once on the NAS (SSH `ssh mlac@100.70.40.114`, prefix docker with `sudo` if
denied; or DSM → Container Manager for the UI equivalents):

```sh
# 1. Is the container up?
/usr/local/bin/docker ps -a --filter name=infosecfollow
#    Up X hours  → running; go to step 2
#    Exited/Restarting → start it:  /usr/local/bin/docker start infosecfollow
#    (on start it immediately runs a full briefing — site recovers in ~5 min)

# 2. What happened at the missed slot? (2>&1 matters: errors are on stderr)
/usr/local/bin/docker logs --since 24h infosecfollow 2>&1 | tail -100
#    "run at HH:MM failed (continuing)" → that run died; the error is right
#    above the line. Common causes below (§5). One-off = ignore; the next
#    slot self-heals. Repeated = fix the cause.

# 3. Force a run right now (don't wait for the next slot):
/usr/local/bin/docker exec infosecfollow /app/run-briefing.sh
#    Watch the output. A clean run ends with "published".
```

Known one-off misses (transient upstream failures, self-healed at the next
slot): Jul 20 12:02, Jul 22 06:02+09:02, Jul 29 16:02. That's the failure
signature of a flaky feed/API window, not a broken system. A **string** of
misses means container down, expired token, or NAS off — §5.

---

## 5. Failure catalog

**5.1 Claude token expired** (~1-year life; created ~mid-June 2026 → renew
by **May 2027**). Symptom: every run fails at the summarize step; docker logs
show the CLI unable to authenticate. Fix: on any logged-in machine run
`claude setup-token`, copy the token, then on the NAS edit
`/volume1/docker/infosecfollow/.env` (`CLAUDE_CODE_OAUTH_TOKEN=...`)
and recreate from that folder: `docker compose up -d` (Container Manager →
project → Action → Build/Up also works). Verify with a manual run (§4.3).

**5.2 GitHub token expired/revoked.** Symptom: runs generate fine, then
`git push` fails 403; commits stop while logs show successful generation.
Fix: new fine-grained PAT at github.com/settings/tokens?type=beta —
Repository access: only `mlac/infosecfollow`; Permissions: **Contents:
Read and write**. Update `GITHUB_TOKEN=` in
`/volume1/docker/infosecfollow/.env`, then `docker compose up -d` from there.

**5.3 NAS rebooted / power loss.** The container has `restart: unless-stopped`
— it comes back on its own and immediately publishes (start-run). Nothing to
do unless someone manually *stopped* it before the reboot (then §4.1).

**5.4 "destination path already exists and is not an empty directory"** in a
clone loop: the data volume got half-initialized. Fix (the `find` form also
removes dot-files like `.gitignore`, which a plain `rm -rf ...*` would miss,
leaving the loop unfixed):
`docker exec infosecfollow sh -c 'find /data/infosecfollow -mindepth 1 -maxdepth 1 -exec rm -rf {} +'`
then `docker restart infosecfollow` (it re-clones cleanly).

**5.5 "push rejected (concurrent update?)"** in logs: harmless race; the next
run resets to origin/main and regenerates. Only investigate if every run says it
— that means something else is pushing to main (is the old Mac LaunchAgent
loaded again? §1).

**5.6 Commit landed but the site didn't update.** GitHub Actions tab → open the
failed "Deploy to GitHub Pages" run → **Re-run all jobs**. The workflow already
retries 3× internally, so a red run usually means a real Pages outage; re-run
when GitHub recovers. (Settings → Pages → Source must stay "GitHub Actions".)

**5.7 Run aborts because feeds won't load.** By design, `generate.py` refuses
to publish when fewer than 2 of the **security** feeds are reachable (log:
`only N security feeds reachable; aborting`) or when none of them yielded
recent items (log: `no recent security items found; aborting`). Almost always
the NAS lost internet or DNS; check general connectivity, then §4.3.

---

## 6. Routine maintenance

- **Rotate both tokens yearly** (§5.1, §5.2). Put a May 2027 reminder in your
  calendar for the Claude token; the PAT expiry is whatever you chose.
- **Engine/content changes** (`engine/*.py`, `engine/feeds.json`, `docs/` templates):
  just push to `main`. Every briefing run starts with `git reset --hard
  origin/main`, so the container picks changes up at the next slot. No rebuild.
- **Deploy-layer changes** (`deploy/scheduler.sh`, `deploy/run-briefing.sh`,
  Dockerfile): these are **baked into the image**. After changing them:
  copy the four files to the NAS compose folder (per `deploy/README.md`) and
  `docker compose up -d --build`.
- **Changing the update schedule**: edit the slot lists in `deploy/scheduler.sh`
  (three places: the `echo` line, the weekday `case` pattern, and the weekend
  `case` pattern), then rebuild as above. Keep the LaunchAgent plist retired
  regardless.
- **Disk hygiene**: container logs are capped (3×10 MB) by compose; the repo
  grows ~25 KB/day in `docs/`. Nothing needs pruning routinely.

Full from-scratch rebuild (new NAS, dead volume): follow `deploy/README.md` —
it walks through both secrets, fetching the four build files, and
`docker compose up -d --build`. Budget ~20 minutes.

---

## 7. Feed publish-time sampler (schedule tuning data)

`engine/feed_pubdates.py` records every feed item's publish timestamp
(deduped by URL) into `logs/feed_pubdates.jsonl` inside the container volume
and prints a distribution report (hour-of-day histograms by group,
weekday/weekend split, freshness lag). Sampled regularly for a week+, this is
the ground truth for choosing update slots.

**Run one snapshot and publish the data** to the `feed-pubdates-data` branch
on GitHub (survives even if the sampler itself fails — the report always
pushes):

```sh
# DSM Task Scheduler → user-defined script → user: root       (or via SSH)
DOCKER=/usr/local/bin/docker; [ -x "$DOCKER" ] || DOCKER=docker
"$DOCKER" exec infosecfollow sh /data/infosecfollow/deploy/snapshot-pubdates.sh
```

- Results: `logs/pubdate_report.txt` (human-readable report) + both `.jsonl`
  files land on the **`feed-pubdates-data`** branch. The push replaces the
  branch each time; the on-volume `.jsonl` keeps accumulating across runs.
- To build a real time series, schedule that same task **hourly** in DSM for a
  week (Schedule tab → Daily → every 1 hour), then read the final report.
- The script is deliberately safe to run at any time: it never touches the
  briefing checkout's HEAD or index (see comments in
  `deploy/snapshot-pubdates.sh`), so colliding with a running briefing cannot
  corrupt either side.
- Requires `deploy/snapshot-pubdates.sh` to be on `main` (the container syncs
  the repo each briefing run; after merging it, wait one slot or run §4.3 once).

---

## 8. Repo facts worth knowing

- **History was truncated on 2026-07-19**: `main` now starts at
  `briefing 2026-07-19 06:05 EDT` (~50 commits). All site data survived as
  files (`docs/archive/` back to 2026-06-12, `docs/data/*.json` daily), but
  per-run git history before Jul 19 is gone — analyses that diff successive
  briefing commits only reach back to Jul 19. If this squash wasn't deliberate,
  treat it as an incident worth understanding before it happens again; the
  container never force-pushes `main`, so it didn't do it.
- **Schedule provenance**: the live schedule is `deploy/scheduler.sh`
  (4 weekday slots, 2 weekend slots, + on-start; wave-aligned as of 2026-07 —
  before that it was 6:02/9:02/12:02/16:02/21:02 daily). The 4-slot
  `com.infosecfollow.refresh.plist` at the repo root is the retired Mac
  LaunchAgent, kept for reference.
- **Branch layout**: `main` = generated site + engine; `feed-pubdates-data` =
  sampler output only (never merge it); `claude/*` = assistant work branches.
