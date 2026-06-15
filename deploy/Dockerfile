# infosecfollow runner: Python engine + Claude Code CLI + cron, for a Synology NAS.
# The app code is NOT baked in; the repo is bind-mounted at /data/infosecfollow
# (see docker-compose.yml) so the container always runs the latest committed code
# and publishes from the same checkout.
FROM python:3.12-slim

# tzdata: ET schedule + date stamps. git: publish to GitHub Pages.
# curl/ca-certificates: install the Claude CLI. ripgrep: used by the CLI.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates tzdata ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI — native install drops the binary in /root/.local/bin.
RUN curl -fsSL https://claude.ai/install.sh | bash
ENV PATH="/root/.local/bin:${PATH}"
ENV INFOSECFOLLOW_CLAUDE_BIN="/root/.local/bin/claude"

# supercronic: a cron that runs in the foreground, inherits the container's
# environment (plain cron strips it, which would drop our auth tokens), logs to
# stdout, and honours $TZ. Pin a version; bump as needed.
ARG SUPERCRONIC_VERSION=v0.2.33
RUN set -eux; \
    case "$(uname -m)" in \
        x86_64)  sc_arch=amd64 ;; \
        aarch64) sc_arch=arm64 ;; \
        *) echo "unsupported arch $(uname -m)" >&2; exit 1 ;; \
    esac; \
    curl -fsSLo /usr/local/bin/supercronic \
        "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${sc_arch}"; \
    chmod +x /usr/local/bin/supercronic

# The CLI persists session state under $HOME/.claude; keep it writable. Disable
# background update/telemetry chatter so an unattended cron run can't hang on it.
ENV HOME=/root \
    DISABLE_AUTOUPDATER=1 \
    DISABLE_TELEMETRY=1 \
    DISABLE_ERROR_REPORTING=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
RUN mkdir -p /root/.claude

WORKDIR /data/infosecfollow
COPY run-briefing.sh /app/run-briefing.sh
COPY crontab /app/crontab
RUN chmod +x /app/run-briefing.sh

# Run one briefing immediately on container start (so you don't wait for the
# first cron slot), then hand off to supercronic for the schedule.
CMD ["/bin/sh", "-c", "/app/run-briefing.sh || true; exec supercronic /app/crontab"]
