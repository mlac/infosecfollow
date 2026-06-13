# infosecfollow

A daily, plain-text briefing site: security, markets, and Pittsburgh.
The engine pulls 18 security feeds plus 9 Pittsburgh-local feeds and 3
commentary feeds (Ed Zitron, Stratechery, Cal Newport), asks Claude to cluster
them into the day's topics (security trends/topics; Pittsburgh business,
around-town, and events — violent-crime stories excluded), pulls weekly-average
market data (S&P 500, Dow, Nasdaq, WTI crude, EUR/GBP/JPY — Yahoo Finance) with
week-over-week trend arrows, Pittsburgh weather (NWS), and Pirates/Steelers/
Penguins scores (ESPN, plaintextsports-style), and renders a static site.

## Layout

```
engine/generate.py   pipeline orchestrator + renderers (Python 3, stdlib only)
engine/market_data.py  weekly-average indexes/oil/FX via Yahoo Finance
engine/pittsburgh.py   NWS weather + ESPN scores for Pittsburgh teams
engine/feeds.json    curated feed groups: security, pittsburgh, reading
docs/index.html      today's briefing (generated)
docs/digest.txt      plain-text rendition of today's briefing
docs/archive/        one .html + .txt per day, plus an index
docs/data/           one .json digest per day (structured archive)
run_daily.sh         cron-friendly wrapper, logs to logs/
```

## Running

```sh
python3 engine/generate.py
```

Requirements: Python 3.9+ and a Claude CLI. The engine finds the CLI in this
order: `$INFOSECFOLLOW_CLAUDE_BIN`, `claude` on PATH, then the binary embedded
in the Claude desktop app. The summarization model defaults to
`claude-opus-4-8`; override with `$INFOSECFOLLOW_MODEL`.

View the site by opening `docs/index.html` directly, or:

```sh
python3 -m http.server -d docs 8000
```

## Scheduling

Run once a day via cron:

```cron
30 7 * * * /Users/mlac/AI_Projects/infosecfollow/run_daily.sh
```

## Behavior notes

- Items window: 24h, widened to 48h automatically when fewer than 12 items.
- Feed failures are tolerated; the run aborts only if fewer than 2 feeds load.
- The model must cite source URLs verbatim from the fetched items; anything
  else is dropped during validation, and invalid JSON is retried once.
- All model and feed text is HTML-escaped before rendering; control characters
  are stripped; the headless Claude call runs with all tools disabled, no MCP
  servers, no user/project settings, in an empty scratch directory.
- If you deploy the site behind a real web server, serve `.txt` files with
  `charset=utf-8` (content may contain non-ASCII characters).
