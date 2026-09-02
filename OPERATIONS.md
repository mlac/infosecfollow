# infosecfollow — Operations Runbook

Everything needed to check, fix, and maintain the site from any machine,
with no AI assistant in the loop. Written 2026-07-29, revised 2026-09-02.

---

## 1. What runs where

```
┌─────────────────────────┐   git push main    ┌──────────────────────────┐
│ Synology NAS            │ ─────────────────► │ GitHub mlac/infosecfollow │
│ "workbench-nas"         │                    │                          │
│ Tailscale 100.70.40.114 │                    │  push to main triggers   │
│                         │                    │  GitHub's built-in        │
│ Docker container        │                    │  "pages build and        │
│  name: infosecfollow    │                    │   deployment" (Source:   │
│  volume:                │                    │   branch main, /docs)    │
│  infosecfollow-data     │                    │      │                   │
│  → /data/infosecfollow  │                    │      ▼                   │
│                         │                    │  GitHub Pages            │
│                         │                    │  https://infosecfollow.com│
└─────────────────────────┘                    └──────────────────────────┘
```

- **The container is the publisher.** `deploy/scheduler.sh` (baked into the
  image) fires `/app/run-briefing.sh` at **7:02, 10:02, 13:32, 19:32 ET on
  weekdays** and **8:02, 19:32 ET on weekends**, plus **once immediately
  whenever the container (re)starts**. Slots sit just after the feeds' four
  daily publish waves (per the 2026-07 publish-time analysis). Each run:
  take the run lock → `git reset --hard origin/main` → `python3
  engine/generate.py` (fetches 57 feeds, calls the Claude CLI to cluster;
  bounded to 25 min) → commit `docs/` → push to `main` (git network calls
  bounded to 2 min). A successful cycle touches
  `/tmp/infosecfollow.last-success` (read by the Docker health check) and,
  if `HEARTBEAT_URL` is set, GETs that URL; a failed cycle exits non-zero and
  GETs `HEARTBEAT_URL/fail`.
- **The site is served by GitHub's built-in Pages pipeline** (Settings →
  Pages → Source: *Deploy from a branch*, `main` `/docs`): every push to
  `main` produces a "pages build and deployment" run in the Actions tab. This
  has been the case all along; the custom deploy workflow added in July never
  switched the source, so both pipelines ran on every push. That workflow is
  now `.github/workflows/redeploy-pages.yml`, a **manual fallback**
  (`workflow_dispatch` only) that re-uploads `docs/` from `main` with three
  deploy attempts and backoff — nothing custom runs on push any more. A stale
  site can therefore be EITHER a missing commit (container problem) OR a
  failed Pages build (GitHub problem).
- **The Mac is not in the loop.** `run_daily.sh` + `com.infosecfollow.refresh.plist`
  are the legacy macOS path, replaced by the NAS. Keep the LaunchAgent
  unloaded (`launchctl bootout gui/$UID/com.infosecfollow.refresh`) so the two
  can never double-publish.

Secrets live in **`/volume1/docker/infosecfollow/.env` on the NAS** (the
compose folder — the four build files sit flat in it; never in the repo):
`CLAUDE_CODE_OAUTH_TOKEN` (Claude subscription token, ~1-year life),
`GITHUB_TOKEN` (fine-grained PAT, Contents R/W on mlac/infosecfollow),
`GIT_REMOTE_URL`, `GIT_AUTHOR_NAME/EMAIL` (a blank value is treated as unset).
Optional: `HEARTBEAT_URL` (dead-man monitor such as healthchecks.io or an
Uptime Kuma push URL; set its grace period to ~15 h), `INFOSECFOLLOW_MODEL`
(default `opus`), `INFOSECFOLLOW_FALLBACK_MODEL` (default `sonnet`),
`INFOSECFOLLOW_ARCHIVE_RETENTION_DAYS` (default 0 = keep everything),
`INFOSECFOLLOW_SCHEDULE_NOTE` (footer sentence). Compose reads `.env` via
`env_file`, so any of these applies with `docker compose up -d` (no rebuild).
Field reference: `deploy/.env.example` in the repo.

---

## 2. The 60-second health check (from any machine)

1. **Is the site current?** Open https://infosecfollow.com — the header shows
   the generation timestamp. Current = no older than the previous slot
   (≤ ~6h during a weekday; the overnight and weekend-midday gaps run ~11h).
2. **Did commits land?** https://github.com/mlac/infosecfollow/commits/main —
   expect a `briefing YYYY-MM-DD HH:MM EDT/EST` commit ~3–5 min after each slot.
3. **Did the deploy succeed?** https://github.com/mlac/infosecfollow/actions —
   the newest **"pages build and deployment"** run should be green.
4. **If a heartbeat monitor is configured** (`HEARTBEAT_URL`), its dashboard is
   the shortcut: green = the last cycle completed; a `/fail` ping or a missed
   check-in = go to §4.

| Symptom | Meaning | Go to |
|---|---|---|
| No commit for the last slot | Container/NAS/API problem | §4 |
| Commit exists, "pages build and deployment" red | Pages build failed | §5.6 |
| Commit exists, Pages run green, site stale | Browser/CDN cache | hard-refresh |

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
# 1. Is the container up, and is it healthy?
/usr/local/bin/docker ps -a --filter name=infosecfollow
#    Up X hours (healthy)   → a cycle completed within the last 15 h; go to step 2
#    Up X hours (unhealthy) → running, but no completed cycle for 15 h; step 2
#    Exited/Restarting → start it:  /usr/local/bin/docker start infosecfollow
#    (on start it immediately runs a full briefing — site recovers in ~5 min)
#    The health check only reports; it never restarts anything.

# 2. What happened at the missed slot? (2>&1 matters: errors are on stderr)
/usr/local/bin/docker logs --since 24h infosecfollow 2>&1 | tail -100
#    "run at HH:MM failed with status N (continuing)" → that run died; the
#    error is right above the line ("generate.py failed", or "push FAILED:"
#    followed by git's message). Common causes below (§5). One-off = ignore;
#    the next slot self-heals. Repeated = fix the cause.
#    "another briefing run is in progress; skipping" → expected when a manual
#    run (or the start-up run) collided with a scheduled one; not a failure.

# 3. Force a run right now (don't wait for the next slot):
/usr/local/bin/docker exec infosecfollow /app/run-briefing.sh
#    Watch the output. A clean run ends with "published". If it says
#    "another briefing run is in progress; skipping" (exit 75), a scheduled or
#    start-up run holds the lock: follow it with `docker logs -f` instead.
```

Known one-off misses (transient upstream failures, self-healed at the next
slot): Jul 20 12:02, Jul 22 06:02+09:02, Jul 29 16:02. That's the failure
signature of a flaky feed/API window, not a broken system. A **string** of
misses means container down, expired token, or NAS off — §5.

---

## 5. Failure catalog

**5.1 Claude token expired** (~1-year life; created ~mid-June 2026 → renew
by **May 2027**). Symptom: every run fails at the summarize step; docker logs
show the CLI unable to authenticate (the error text talks about login /
authentication / an invalid token — if it names a *model* instead, that is
§5.8). Fix: on any logged-in machine run `claude setup-token`, copy the
token, then on the NAS edit `/volume1/docker/infosecfollow/.env`
(`CLAUDE_CODE_OAUTH_TOKEN=...`) and recreate from that folder:
`docker compose up -d` (Container Manager → project → Action → Build/Up also
works). Verify with a manual run (§4.3).

**5.2 GitHub token expired/revoked.** Symptom: runs generate fine, then the
log shows `push FAILED:` with git's 403 text, the scheduler logs `run at
HH:MM failed with status 1 (continuing)`, and the heartbeat monitor (if any)
receives `/fail`; commits stop while generation succeeds. (Before 2026-09
this was disguised as the harmless "concurrent update" message.) Fix: new
fine-grained PAT at github.com/settings/tokens?type=beta — Repository access:
only `mlac/infosecfollow`; Permissions: **Contents: Read and write**. Update
`GITHUB_TOKEN=` in `/volume1/docker/infosecfollow/.env`, then
`docker compose up -d` from there.

**5.3 NAS rebooted / power loss.** The container has `restart: unless-stopped`
— it comes back on its own and immediately publishes (start-run). A clean
shutdown sends SIGTERM: the scheduler lets an in-flight run finish (compose grants a 30-minute grace period, sized to the longest
possible run; a NAS reboot's own service timeout may be shorter) and exits. Nothing to do unless someone
manually *stopped* it before the reboot (then §4.1).

**5.4 Half-initialised data volume (note — now automatic).** The old clone
loop "destination path already exists and is not an empty directory" is
handled by `run-briefing.sh` itself: a `/data/infosecfollow` without `.git` is
cleared (including dot-files) before the clone, and the log says
`clearing half-initialised /data/infosecfollow`. No manual `find`/`rm` is
needed any more; `docker restart infosecfollow` is enough if it ever loops.

**5.5 "push rejected (concurrent update); next run will regenerate from
origin"** in logs: a genuine non-fast-forward race (someone pushed to `main`
at the same moment); harmless, the run still counts as a success and the next
run resets to origin/main and regenerates. Any *other* push failure is logged
as `push FAILED:` and fails the run (§5.2). Only investigate the race message
if every run says it — that means something else is pushing to main (is the
old Mac LaunchAgent loaded again? §1).

**5.6 Commit landed but the site didn't update.** GitHub Actions tab → open
the newest red **"pages build and deployment"** run → **Re-run all jobs**. If
that pipeline is stuck or keeps failing, trigger **"Redeploy to GitHub Pages
(manual)"** (Actions → that workflow → *Run workflow*): it re-uploads `docs/`
from `main` with three deploy attempts and backoff. A red built-in run
usually means a real Pages outage; re-run when GitHub recovers. Settings →
Pages → Source should read *Deploy from a branch*, `main` `/docs`.

**5.7 Run aborts because feeds won't load.** By design, `generate.py` refuses
to publish when fewer than 2 of the **security** feeds are reachable (log:
`only N security feeds reachable; aborting`) or when none of them yielded
recent items (log: `no recent security items found; aborting`). Almost always
the NAS lost internet or DNS; check general connectivity, then §4.3.

**5.8 Summarize step fails with a model error** (model not found / retired /
overloaded). The engine asks for the CLI alias `opus` with `--fallback-model
sonnet`, so a retired or overloaded primary normally falls through to the
fallback on its own (the Feed Health section and `meta.served_by` in the day's
JSON show which model actually served the run). If the log shows all 3 CLI
attempts failing even with the fallback in place, set `INFOSECFOLLOW_MODEL` and
`INFOSECFOLLOW_FALLBACK_MODEL` in `/volume1/docker/infosecfollow/.env` to
explicit model ids and `docker compose up -d`. Distinguish from §5.1 by the
error text: an auth failure talks about login/tokens, a model failure names
the model.

---

## 6. Routine maintenance

- **Rotate both tokens yearly** (§5.1, §5.2). Put a May 2027 reminder in your
  calendar for the Claude token; the PAT expiry is whatever you chose.
- **Bump the pinned Claude CLI**: change `ARG CLAUDE_CLI_VERSION` in
  `deploy/Dockerfile`, copy it to the NAS compose folder, `docker compose up -d
  --build`, then run one manual cycle (§4.3) and check it ends in `published`.
- **Engine/content changes** (`engine/*.py`, `engine/feeds.json`, the
  renderers in `engine/generate.py`): just push to `main`. CI
  (`.github/workflows/ci.yml`) runs the unit tests on any push touching
  `engine/` or `deploy/`; it cannot block the push (no branch protection), but
  GitHub emails a red run within about a minute — fix before the next slot.
  Every briefing run starts with `git reset --hard origin/main`, so the
  container picks changes up at the next slot. No rebuild.
- **Deploy-layer changes** (`deploy/scheduler.sh`, `deploy/run-briefing.sh`,
  `deploy/Dockerfile`, `deploy/docker-compose.yml`): these are **baked into the
  image**. After changing any of them: copy the four files to the NAS compose
  folder (per `deploy/README.md`) and `docker compose up -d --build`. The
  2026-09 change set touched all four, so it needs one such rebuild.
- **`.env` changes** (tokens, `HEARTBEAT_URL`, `INFOSECFOLLOW_*` knobs):
  `docker compose up -d` from the compose folder; no rebuild.
- **Changing the update schedule**: edit `WEEKDAY_SLOTS` / `WEEKEND_SLOTS` at
  the top of `deploy/scheduler.sh` (two variables, HH:MM in the container's
  `TZ`), then rebuild as above. Update `INFOSECFOLLOW_SCHEDULE_NOTE` in `.env`
  (or its default in `engine/generate.py`) so the page footer matches. Keep
  the LaunchAgent plist retired regardless.
- **Disk hygiene**: container logs are capped (3×10 MB) by compose. Each run
  adds an archive `.html` + `.txt` pair to `docs/archive/` and rewrites the
  day's `docs/data/<date>.json` (~25 KB), so `docs/` grows roughly 0.2–0.4 MB
  per day, with about the same again in `.git` objects inside the container
  volume. Nothing needs pruning routinely; if it ever does, set
  `INFOSECFOLLOW_ARCHIVE_RETENTION_DAYS=N` in `.env` (keep N ≥ 7 — the
  engine's memory and diff look back 7 days) and archive/data files older
  than N days are deleted at the next run.

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
on GitHub. The branch is created by the first snapshot — as of 2026-09-02 it
does not exist on GitHub, so this task has never run through the script (or
its branch was deleted). The report is pushed even when the sampler itself
fails, and `deploy/snapshot-pubdates.sh` exits non-zero if either the sampler
or the push failed, so a DSM task can tell:

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

- **History is complete.** `main` runs from the first commit `7adc7e6`
  ("infosecfollow: daily AI security briefing site + engine", 2026-06-12) to
  today — 386+ commits as of 2026-09-02, with one merge commit (PR #6). If a
  checkout appears to start mid-stream (e.g. at a `briefing …` commit, ~50
  commits deep), it is a **shallow clone**: Claude Code web sessions and
  `git clone --depth` produce depth-50 clones. Check for a `.git/shallow` file
  or run `git fetch --unshallow` before concluding history is missing. The
  container never force-pushes `main`.
- **Schedule provenance**: the live schedule is `deploy/scheduler.sh`
  (`WEEKDAY_SLOTS` / `WEEKEND_SLOTS`: 4 weekday slots, 2 weekend slots, + on-start;
  wave-aligned as of 2026-07 — before that it was 6:02/9:02/12:02/16:02/21:02
  daily). The 4-slot `com.infosecfollow.refresh.plist` at the repo root is the
  retired Mac LaunchAgent, kept for reference.
- **Branch layout**: `main` = generated site + engine (no branch protection);
  `feed-pubdates-data` = sampler output only, created by the first snapshot
  (never merge it); `claude/*` = assistant work branches.
