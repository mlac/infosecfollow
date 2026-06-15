# Running infosecfollow on a Synology NAS

This runs the briefing engine in a Docker container on your NAS (`workbench-nas`)
on a 6am / noon / 4pm / 9pm ET schedule, so your Mac no longer has to be on. The
container regenerates the site and pushes it to GitHub Pages, exactly like the old
macOS LaunchAgent did.

**How it works:** the container holds Python + the Claude Code CLI + a cron
(`supercronic`). It builds straight from this public repo's `deploy/` folder and,
on first run, **clones the app into a Docker volume itself** — so the NAS host
needs nothing but Docker (no `git` required). Authentication uses your **Claude
subscription** via a long-lived token (no API-key billing) and a **GitHub token**
for the clone/push.

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

Then grab the compose file (no git needed — curl it from the public repo):

```sh
curl -fsSLo docker-compose.yml \
  https://raw.githubusercontent.com/mlac/infosecfollow/main/deploy/docker-compose.yml
```

---

## 3. Build and start

```sh
cd /volume1/docker/infosecfollow
docker compose up -d --build
```

This builds the image from the repo's `deploy/` folder and starts the container,
which clones the app into a Docker volume and runs one briefing immediately, then
follows the cron schedule. Watch it:

```sh
docker logs -f infosecfollow
```

You should see `cloning …`, the engine's `[1/4]…[4/4]` lines, and `published`.
Within a minute the live site updates.

> **If the build errors on the URL context** (older Compose): build the image
> directly, then start.
> ```sh
> docker build -t infosecfollow-runner \
>   "https://github.com/mlac/infosecfollow.git#main:deploy"
> docker compose up -d          # uses the prebuilt infosecfollow-runner image
> ```

---

## 4. Turn off the Mac LaunchAgent

So the two don't double-publish, disable the old schedule on your Mac:

```sh
launchctl bootout gui/$(id -u)/com.infosecfollow.refresh 2>/dev/null || \
  launchctl unload ~/Library/LaunchAgents/com.infosecfollow.refresh.plist
```

The Mac can stay off from here on.

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
