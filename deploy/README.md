# Running infosecfollow on a Synology NAS

This runs the briefing engine in a Docker container on your NAS (`workbench-nas`)
on a 6am / noon / 4pm / 9pm ET schedule, so your Mac no longer has to be on. The
container regenerates the site and pushes it to GitHub Pages, exactly like the old
macOS LaunchAgent did.

**How it works:** the container holds Python + the Claude Code CLI + a cron
(`supercronic`). The app code is *not* baked into the image — the repo is
bind-mounted from the NAS, so the container runs whatever is committed and
publishes from that same checkout. Authentication uses your **Claude
subscription** via a long-lived token (no API-key billing) and a **GitHub token**
for the push.

---

## 1. Collect two secrets (on your Mac)

**a) Claude subscription token** — on your logged-in Mac, run:

```sh
claude setup-token
```

It opens a browser, then prints a token (valid ~1 year). Copy it. This lets the
container use your Pro/Max subscription headlessly — no per-call API charges.

**b) GitHub access token** — at GitHub → Settings → Developer settings →
**Fine-grained tokens** → Generate new token:
- Repository access: only `mlac/infosecfollow`
- Permissions: **Contents → Read and write**
- Expiration: your choice (set a reminder to rotate)

Copy that token too.

---

## 2. Put the repo on the NAS

SSH in (`ssh workbench-nas`) and clone into the standard Docker shared folder
**over HTTPS** (so the token can authenticate):

```sh
mkdir -p /volume1/docker
git clone https://github.com/mlac/infosecfollow.git /volume1/docker/infosecfollow
```

If your NAS has a different volume, use that path and update the bind-mount in
`deploy/docker-compose.yml`.

---

## 3. Create the secrets file

```sh
cd /volume1/docker/infosecfollow/deploy
cp .env.example .env
vi .env        # paste CLAUDE_CODE_OAUTH_TOKEN and GITHUB_TOKEN
```

`.env` is gitignored — it stays on the NAS and is never committed.

---

## 4. Build and start

**Container Manager (GUI):** open Container Manager → **Project** → Create →
set the path to `/volume1/docker/infosecfollow/deploy` (it finds
`docker-compose.yml`) → build and run.

**Or via SSH:**

```sh
cd /volume1/docker/infosecfollow/deploy
sudo docker compose up -d --build
```

The container runs one briefing immediately on startup, then follows the cron
schedule. Watch it:

```sh
sudo docker logs -f infosecfollow
```

You should see `===== run ... =====`, the engine's `[1/4]…[4/4]` lines, and
`published`. Within a minute the live site updates.

---

## 5. Turn off the Mac LaunchAgent

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
sudo docker exec infosecfollow /app/run-briefing.sh

# Check the CLI authenticated (should print account/usage, not "Not logged in"):
sudo docker exec infosecfollow claude --version

# Rebuild after pulling engine changes (not usually needed — the container
# git-resets to origin/main each run and picks up code automatically):
sudo docker compose up -d --build
```

**Common issues**
- *"Not logged in" / auth errors:* `CLAUDE_CODE_OAUTH_TOKEN` is wrong or expired —
  regenerate with `claude setup-token` and update `.env`, then
  `docker compose up -d`.
- *Push rejected / 403:* the `GITHUB_TOKEN` lacks Contents write or expired.
- *Wrong times:* confirm `TZ: America/New_York` in `docker-compose.yml`.

## Maintenance
- **Claude token** expires ~1 year out — rotate with `claude setup-token`.
- **GitHub token** — rotate per the expiry you chose.
- After changing `.env`, apply with `sudo docker compose up -d` (no rebuild
  needed).
