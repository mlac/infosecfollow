# infosecfollow

A plain-text briefing site, regenerated several times a day: security,
business and politics, markets, and Pittsburgh. The engine pulls 57 feeds in
seven groups (`engine/feeds.json`): 24 security feeds, 9 Pittsburgh-local
feeds, 8 business/politics feeds (WSJ ×4, The Economist, FT ×3), 4 Pittsburgh
arts/events feeds, 6 sports-media feeds (Steelers/Pirates podcasts, YouTube,
beat writers), 3 Team USA feeds (ESPN Soccer, ESPN Olympics, Guardian
Olympics), and 3 commentary feeds (Ed Zitron, Stratechery, Cal Newport). It
asks Claude to cluster them into the day's topics (security trends/topics;
Pittsburgh business, around-town, and events — violent-crime stories excluded;
business/politics, team, and Team USA items), pulls weekly-average market data
(S&P 500, Dow, Nasdaq, WTI crude, EUR/GBP/JPY — Yahoo Finance) with
week-over-week trend arrows, Pittsburgh weather (NWS), and Pirates/Steelers/
Penguins scores (ESPN, falling back to plaintextsports.com team pages when
ESPN fails), and renders a static site.

## Layout

```
engine/generate.py       pipeline orchestrator + renderers (Python 3, stdlib only)
engine/safefetch.py      SSRF guard, bounded reads, DTD-free XML parsing
engine/market_data.py    weekly-average indexes/oil/FX via Yahoo Finance
engine/pittsburgh.py     NWS weather + ESPN scores for Pittsburgh teams, with the
                         plaintextsports fallback wiring
engine/plaintextsports.py parser for plaintextsports.com team pages (fixtures in
                         engine/testdata/pts/)
engine/feed_pubdates.py  feed publish-time sampler (schedule tuning; OPERATIONS.md §7)
engine/feeds.json        curated feed groups: security, pittsburgh, bizpol, events,
                         sports_media, team_usa, reading
engine/test_*.py         unit tests (generate, plaintextsports, hardening)
docs/index.html          today's briefing (generated)
docs/digest.txt          plain-text rendition of today's briefing
docs/archive/            one .html + .txt per run (YYYY-MM-DD-HHMM), plus an index
docs/data/               one .json record per day (structured archive; rewritten by each run)
deploy/                  the NAS container: Dockerfile, run-briefing.sh, scheduler.sh,
                         docker-compose.yml, .env.example, README
.github/workflows/       ci.yml (tests on push/PR); redeploy-pages.yml (manual Pages fallback)
OPERATIONS.md            runbook: health check, failure catalog, maintenance
```

## Running

```sh
python3 engine/generate.py
```

Requirements: Python 3.9+ (`zoneinfo`; the container runs 3.12, CI tests 3.11
and 3.12) and a Claude CLI. The engine finds the CLI in this order:
`$INFOSECFOLLOW_CLAUDE_BIN` (an error if set but not executable), `claude` on
PATH, then the binary embedded in the Claude desktop app. It asks for the CLI
model alias `opus` (the newest Opus at run time) with `--fallback-model sonnet`
(the newest Sonnet), so a retired or overloaded model no longer kills a run;
override either with `$INFOSECFOLLOW_MODEL` and `$INFOSECFOLLOW_FALLBACK_MODEL`
(aliases or full model ids). The model ids that actually served each run are
recorded in `docs/data/<date>.json` under `meta.served_by` (with
`meta.model_calls`, `meta.model_cost_usd`, `meta.model_duration_ms`) and shown
in the page's Feed Health section.

Other knobs: `$INFOSECFOLLOW_ARCHIVE_RETENTION_DAYS` (default 0 = keep
everything), `$INFOSECFOLLOW_SCHEDULE_NOTE` (the footer sentence describing
the update schedule), `$INFOSECFOLLOW_SITE_URL` (canonical link).

View the site by opening `docs/index.html` directly, or:

```sh
python3 -m http.server -d docs 8000
```

## Sections

Every page (and `digest.txt`) carries, in order, whichever of these have content:

- **Emerging Trends and Key Updates** — a curated glance at the day; entries are
  labelled new/updated against the previous run, keyed on any shared source
  URL (an entry linking several stories takes the strongest change).
- **Security** — up to 10 topics, carried forward through the day.
- **Business and Politics**
- **Pittsburgh** — weather, business, around town, events.
- **Sports** — scores, Around the Teams, Team USA.
- **Reading** — collapsed by default on the page.
- **Markets** — collapsed by default on the page.
- **Feed Health** — per group: feeds loaded vs total, items in window, failed
  feeds with the error text, loaded feeds with no recent items; markets /
  weather / scores status with error text (e.g. an ESPN 403) and which score
  source each run used; the model ids, call count, model time and list-price
  cost of the run. The same data is stored as `feed_health` in the day's JSON,
  and `meta.feed_failures` lists the failed feed names. Collapsed by default on
  the page.

Reading, Markets and Feed Health render as closed `<details>` blocks: standing
reference rather than what changed today, one click from the summary row. The
plain-text digest keeps every section inline. The page's only script opens a
folded section when a link targets something inside it (a "Jump to" entry, or
an at-a-glance link to a reading item); without JavaScript the folds still open
on click.

The page also has a skip link, a "Jump to" section index, meta description /
Open Graph tags, a canonical link on the index page, archive titles that
include the run time, and a footer stating the update schedule.

## Scheduling

Production runs in the NAS container under `deploy/`: **07:02, 10:02, 13:32
and 19:32 ET on weekdays, 08:02 and 19:32 ET on weekends, plus once on
container start** — see `deploy/README.md` and `OPERATIONS.md`. The macOS
LaunchAgent that preceded it was removed in 2026-09; `git log -- run_daily.sh`
still has it if it is ever wanted.

## Tests

From the repo root:

```sh
python3 -m unittest discover -s engine -p 'test_*.py'
```

(`python3 -m unittest engine/test_hardening.py` does not work from the root.)
CI (`.github/workflows/ci.yml`) runs `py_compile`, `feeds.json` validation,
the unit tests on Python 3.11 and 3.12, and `sh -n` on the shell scripts, on
any push or pull request that touches `engine/`, `deploy/` or the workflow
itself; briefing commits touch only `docs/` and never trigger it.
It cannot block a bad push (no branch protection), but GitHub emails a red run
within about a minute.

## Behavior notes

- Windows: security 24h, widened to 48h automatically when fewer than 12 items
  (the page then shows a "Quiet day" note); Pittsburgh 48h; business/politics
  36h; events 120h; sports media 96h; Team USA 72h; reading 14 days. All 57
  feeds are fetched through one 8-worker pool; each fetch is bounded to 8 MiB
  and 60 s wall clock.
- Feed failures are tolerated and reported in Feed Health; the run aborts only
  if fewer than 2 **security** feeds load or no security item falls in the
  window.
- Carry-forward: each run reads today's earlier record and passes its topics
  and local items to the model as `TODAY_SO_FAR` / `TODAY_SO_FAR_LOCAL`, with
  instructions to keep them (same titles, text unchanged unless something new
  happened, sources re-cited) and add new stories on top, up to 10 security
  topics — so an evening reader still sees the morning's stories. Only prior
  days feed the "age out stagnated stories" rule, and the sources of carried
  items stay citable after they age out of the fetch window.
- If the local-sections model call fails, the previous good local block (from
  today or yesterday) is reused and the page and `digest.txt` carry a note
  saying which run it came from; the day's JSON is never overwritten with
  `local: null`.
- The model must cite source URLs verbatim from the fetched (or carried) items;
  anything else is dropped during validation, and invalid JSON is retried once
  with a repair note. A process-level CLI failure (crash, API/auth error,
  timeout) is retried up to 3 times with 30 s then 90 s backoff.
- All model and feed text is HTML-escaped before rendering; control characters
  and invisible bidi/zero-width characters are stripped from feed text and
  from model output during validation. The headless Claude call runs with
  `--tools ""` (no built-in tools) plus a denylist, `--no-session-persistence`,
  `--strict-mcp-config`, `--setting-sources ""`, in an empty scratch
  directory, with `GITHUB_TOKEN`/`GH_TOKEN`/`GIT_*` removed from its
  environment.
- Archive: one `.html` + `.txt` per run under `docs/archive/` plus an index,
  and one JSON per day under `docs/data/` (rewritten by each run of the day;
  it also stores glance, notes and feed_health). Retention is off by default;
  `INFOSECFOLLOW_ARCHIVE_RETENTION_DAYS=N` prunes archive and data files older
  than N days.
- If you deploy the site behind a real web server, serve `.txt` files with
  `charset=utf-8` (content may contain non-ASCII characters).
