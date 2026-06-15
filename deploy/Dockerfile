# infosecfollow runner: Python engine + Claude Code CLI + a tiny scheduler, for a
# Synology NAS. The app code is NOT baked in; the container clones the repo into a
# Docker volume on first run (see run-briefing.sh) and publishes from it.
FROM python:3.12-slim

# tzdata: ET schedule + date stamps. git: clone/publish. curl/ca-certificates:
# install the Claude CLI. ripgrep: used by the CLI.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates tzdata ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI — native install drops the binary in /root/.local/bin.
RUN curl -fsSL https://claude.ai/install.sh | bash
ENV PATH="/root/.local/bin:${PATH}"
ENV INFOSECFOLLOW_CLAUDE_BIN="/root/.local/bin/claude"

# The CLI persists session state under $HOME/.claude; keep it writable. Disable
# background update/telemetry chatter so an unattended run can't hang on it.
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

# A plain shell scheduler (not cron/supercronic): it inherits the container's
# environment, has no PID-1 quirks, and just calls run-briefing.sh on the schedule.
CMD ["/app/scheduler.sh"]
