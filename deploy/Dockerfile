# infosecfollow runner: Python engine + Claude Code CLI + a tiny scheduler, for a
# Synology NAS. The app code is NOT baked in; the container clones the repo into a
# Docker volume on first run (see run-briefing.sh) and publishes from it.
FROM python:3.12-slim

# tzdata: ET schedule + date stamps. git: clone/publish. curl/ca-certificates:
# install the Claude CLI and ping the heartbeat monitor. ripgrep: used by the CLI.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates tzdata ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI — native install drops the binary in /root/.local/bin. The
# version is PINNED: engine/generate.py's argv (--tools, --fallback-model,
# --no-session-persistence, --setting-sources, --output-format json) is tested
# against it, and an unpinned install would take whatever is current at
# rebuild time. To move to a newer CLI: change CLAUDE_CLI_VERSION, rebuild
# (`docker compose up -d --build`), and check one manual run.
ARG CLAUDE_CLI_VERSION=2.1.258
RUN curl -fsSL https://claude.ai/install.sh | bash -s "$CLAUDE_CLI_VERSION"
ENV PATH="/root/.local/bin:${PATH}"
ENV INFOSECFOLLOW_CLAUDE_BIN="/root/.local/bin/claude"

# The CLI persists state under $HOME/.claude; keep it writable. Disable
# background update/telemetry chatter so an unattended run can't hang on it
# (the engine also passes --no-session-persistence, so transcripts are not
# written to the container layer on every call).
ENV HOME=/root \
    DISABLE_AUTOUPDATER=1 \
    DISABLE_TELEMETRY=1 \
    DISABLE_ERROR_REPORTING=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
RUN mkdir -p /root/.claude

WORKDIR /data/infosecfollow
COPY run-briefing.sh /app/run-briefing.sh
COPY scheduler.sh /app/scheduler.sh
RUN chmod +x /app/run-briefing.sh /app/scheduler.sh

# Healthy = a briefing cycle completed within the last 15 hours (the longest
# scheduled gap is the weekend evening-to-morning 12.5 h). Shows in
# `docker ps` as (healthy)/(unhealthy); it does not restart anything.
HEALTHCHECK --interval=10m --timeout=5s --start-period=20m --retries=1 \
    CMD sh -c '[ -f /tmp/infosecfollow.last-success ] && [ $(( $(date +%s) - $(stat -c %Y /tmp/infosecfollow.last-success) )) -lt 54000 ]'

# A plain shell scheduler (not cron/supercronic): it inherits the container's
# environment, has no PID-1 quirks (compose runs it under an init), and just
# calls run-briefing.sh on the schedule.
CMD ["/app/scheduler.sh"]
