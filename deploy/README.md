# Running infosecfollow on a Synology NAS

This runs the briefing engine in a Docker container on your NAS (`workbench-nas`)
on a 6am / noon / 4pm / 9pm ET schedule, so your Mac no longer has to be on. The
container regenerates the site and pushes it to GitHub Pages, exactly like the old
macOS LaunchAgent did.

**How it works:** the container holds Python + the Claude Code CLI + git + a tiny
shell scheduler. You fetch a few build files with `curl`, build the image
locally, and on first run the container **clones the app into a Docker volume
itself** (using the git bundled inside the image) — so the NAS host needs no git
at all. Authentication uses your **Claude subscription** via a long-lived token
(no API-key billing) and a **GitHub token** for the clone/push.

Prereqs on the NAS: Container Manager (Docker) — confirmed present — and your user
in the `docker` group (so no `sudo`).

---

## 1. Collect two secrets (on your Mac)

**a) Claude subscription token** — in a local Mac terminal:

```sh
claude setup-token
```

It opens a browser, then prints a token (valid ~1 year). Copy it. This lets the
container use your Pro/Max subscription headlessly — no per-call API charges.

**b) GitHub access token** — at https://github.com/settings/tokens?type=beta
(Fine-grained tokens) → Generate new token:
- Repository access: only `mlac/infosecfollow`
- Permissions: **Contents → Read and write**
- Expiration: your choice (set a reminder to rotate)

Copy that token too.

---

## 2. Create the working dir + secrets file (on the NAS)

SSH in (`ssh workbench-nas`) and make a folder with the `.env`:

```sh
mkdir -p /volume1/docker/infosecfollow
cd /volume1/docker/infosecfollow

cat > .env <<'EOF'
CLAUDE_CODE_OAUTH_TOKEN=
GITHUB_TOKEN=
GIT_REMOTE_URL=https://github.com/mlac/infosecfollow.git
GIT_AUTHOR_NAME=infosecfollow-bot
GIT_AUTHOR_EMAIL=infosecfollow@users.noreply.github.com
EOF

vi .env   # paste your two tokens after the = signs
```

`.env` stays on the NAS and is never committed.

Then fetch the four build files into this folder with `curl` (the NAS has no git,
so we don't clone — the container does its own clone at runtime):

```sh
base=https://raw.githubusercontent.com/mlac/infosecfollow/main/deploy
for f in Dockerfile run-briefing.sh scheduler.sh docker-compose.yml; do
  curl -fsSLo "$f" "$base/$f"
done
```

---

## 3. Build and start

```sh
cd /volume1/docker/infosecfollow
docker compose up -d --build
```

This builds the image from the local folder and starts the container, which
clones the app into a Docker volume and runs one briefing immediately, then
follows the schedule. Watch it:

```sh
docker logs -f infosecfollow
```

You should see `cloning …`, the engine's `[1/4]…[4/4]` lines, and `published`.
Within a minute the live site updates.

---

## 4. Turn off the Mac LaunchAgent

So the two don't double-publish, disable the old schedule on your Mac:

```sh
launchctl bootout gui/$(id -u)/com.infosecfollow.refresh 2>/dev/null || \
  launchctl unload ~/Library/LaunchAgents/com.infosecfollow.refresh.plist
```

The Mac can stay off from here on.

---

## Development workflow (editing the code afterwards)

GitHub `main` is the single source of truth. **Always edit on the Mac and push;
never edit on the NAS** — the container runs `git reset --hard origin/main` every
cycle, so any local change in its volume is wiped on the next run.

**Engine / content / feeds** (`engine/*.py`, `feeds.json`) update **automatically**
— the container resets to `origin/main` before each run, so the next scheduled run
uses your new code. From the Mac:

```sh
git pull --rebase        # see the gotcha below
# ...edit...
git commit -am "..."
git push
```

To apply a change immediately instead of waiting for the next slot, run one cycle
on the NAS:

```sh
docker exec infosecfollow /app/run-briefing.sh
```

**Container plumbing** (`deploy/Dockerfile`, `deploy/run-briefing.sh`,
`deploy/scheduler.sh`) is baked into the image — the container runs `/app/...`, not
the repo copies — so changing it needs a rebuild on the NAS after you push:

```sh
cd /volume1/docker/infosecfollow
base=https://raw.githubusercontent.com/mlac/infosecfollow/main/deploy
for f in Dockerfile run-briefing.sh scheduler.sh docker-compose.yml; do curl -fsSLo "$f" "$base/$f"; done
docker compose up -d --build
```

**Gotcha — pull before you push.** The NAS pushes a `briefing …` commit to `main`
~4×/day, so your Mac's local `main` falls behind constantly. Start every editing
session with `git pull --rebase`; if a push is rejected as non-fast-forward, just
`git pull --rebase` and push again. Your `engine/` edits and the NAS's `docs/`
commits never touch the same files, so it replays cleanly.

---

## Run on demand / troubleshooting

```sh
# Trigger a briefing right now:
docker exec infosecfollow /app/run-briefing.sh

# Confirm the CLI authenticated (prints a version, not "Not logged in"):
docker exec infosecfollow claude --version

# Update after you push engine changes — usually unnecessary (the container
# git-resets to origin/main each run). Only rebuild for Dockerfile/runner changes:
docker compose up -d --build
```

**Common issues**
- *"Not logged in" / auth errors:* `CLAUDE_CODE_OAUTH_TOKEN` is wrong or expired —
  regenerate with `claude setup-token`, update `.env`, then `docker compose up -d`.
- *Clone/push rejected (403):* the `GITHUB_TOKEN` lacks Contents write or expired.
- *Wrong times:* confirm `TZ: America/New_York` in `docker-compose.yml`.
- *Start over clean:* `docker compose down -v` removes the container **and the
  cloned volume**; the next `up` re-clones.

## Maintenance
- **Claude token** expires ~1 year out — rotate with `claude setup-token`.
- **GitHub token** — rotate per the expiry you chose.
- After changing `.env`, apply with `docker compose up -d` (no rebuild needed).
