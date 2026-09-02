"""Pittsburgh weather (National Weather Service) and pro sports (ESPN, with
plaintextsports.com team pages as the fallback when ESPN fails), formatted as
plain-text blocks in the spirit of plaintextsports.com, with game links into
plaintextsports.com. Stdlib only, no API keys.
"""

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import plaintextsports as pts
import safefetch

TIMEOUT = 20            # per socket operation
DEADLINE = 45           # whole response, wall clock
MAX_BYTES = 4_000_000
TZ = ZoneInfo("America/New_York")
USER_AGENT = "infosecfollow/1.0 (https://infosecfollow.com)"
# site.api.espn.com answers 403 to non-browser User-Agents (since 2026-08-04);
# NWS, by contrast, asks API clients for a contact UA — so ESPN gets a
# browser-shaped request and everything else keeps USER_AGENT.
BROWSER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                 "AppleWebKit/537.36 (KHTML, like Gecko) "
                 "Chrome/128.0.0.0 Safari/537.36")
ESPN_HEADERS = {
    "User-Agent": BROWSER_AGENT,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.espn.com/",
    "Origin": "https://www.espn.com",
}
NWS_POINT = "https://api.weather.gov/points/40.4406,-79.9959"  # downtown Pittsburgh
ESPN = "https://site.api.espn.com/apis/site/v2/sports"
LEAGUES = [("baseball", "mlb"), ("football", "nfl"), ("hockey", "nhl")]
TEAM_ABBR = "PIT"
NEXT_GAME_HORIZON = timedelta(days=15)  # covers an NFL bye week; skips off-season


def _get_raw(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {
        "User-Agent": USER_AGENT, "Accept": "application/json"})
    with safefetch.safe_open(req, timeout=TIMEOUT) as resp:
        return safefetch.read_bounded(resp, MAX_BYTES, DEADLINE)


def _get_json(url, headers=None):
    return json.loads(_get_raw(url, headers).decode("utf-8", "replace"))


def _get_text(url, headers=None):
    return _get_raw(url, headers).decode("utf-8", "replace")


_SERVER_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ./_-]{0,31}")


def _reason(exc):
    """Publishable text for a failure: only messages this engine composed.

    Feed Health publishes these strings on the public page, and a remote
    server controls the text of many stdlib exceptions (a bogus status line,
    an error body, a hostile Server header). RuntimeError and ValueError here
    are always ours — _http_error's "HTTP <code> (server: <token>)" and
    plaintextsports' "not a team page (...)" — so they are relayed; anything
    else is published as its class name and logged in full by the caller.
    """
    if isinstance(exc, (RuntimeError, ValueError)):
        return " ".join(str(exc).split())[:160]
    return type(exc).__name__


def _http_error(label, exc):
    """Log an HTTPError with its server header and a body excerpt, so a block
    page (Akamai, Cloudflare) is identifiable in the run log, and return the
    RuntimeError to raise. The raised message carries only the status code
    and a product-token-shaped server name, because error strings are
    published in the site's Feed Health section and must not relay
    attacker-chosen prose. The excerpt comes from a single bounded read, so a
    slow-drip error body cannot stall the run."""
    try:
        fp = getattr(exc, "fp", None)
        body = fp.read1(600).decode("utf-8", "replace") if fp is not None else ""
    except Exception:
        body = ""
    body = " ".join(body.split())[:200]
    server = exc.headers.get("Server", "") if exc.headers else ""
    print(f"  sports: {label} -> HTTP {exc.code} {exc.reason}"
          + (f" (server: {' '.join(server.split())[:80]})" if server else "")
          + (f": {body}" if body else ""))
    if not _SERVER_TOKEN.fullmatch(server):
        server = ""
    return RuntimeError(f"HTTP {exc.code}" + (f" (server: {server})" if server else ""))


def _espn_json(path):
    """ESPN's public site API with browser-shaped headers; see _http_error."""
    try:
        return _get_json(f"{ESPN}{path}", headers=ESPN_HEADERS)
    except urllib.error.HTTPError as exc:
        raise _http_error(f"ESPN {path}", exc) from None


def weather_lines():
    """First three NWS forecast periods, e.g. 'Today: Sunny, high 84F.'"""
    forecast_url = _get_json(NWS_POINT)["properties"]["forecast"]
    periods = _get_json(forecast_url)["properties"]["periods"][:3]
    lines = []
    for p in periods:
        hilo = "high" if p.get("isDaytime") else "low"
        lines.append(f"{p['name']}: {p['shortForecast']}, "
                     f"{hilo} {p['temperature']}{p['temperatureUnit']}.")
    return lines


# ----------------------------------------------------------------- sports

def _parse_when(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)


# ESPN abbreviations differ from plaintextsports slugs for some teams.
_PTS_ABBR = {
    "mlb": {"CHW": "cws"},
    "nhl": {"TB": "tbl", "NJ": "njd", "SJ": "sjs", "LA": "lak"},
    "nfl": {"WSH": "was"},
}
# ESPN season.type -> plaintextsports NFL week-slug prefix
_NFL_PLAYOFF = {1: "wild-card", 2: "divisional", 3: "conference", 5: "super-bowl"}


def _pts_slug(league, abbr):
    return _PTS_ABBR.get(league, {}).get(abbr.upper(), abbr.lower())


def _nfl_week_seg(event):
    """plaintextsports NFL path segment '{year}/{week-slug}' from an ESPN event.

    Scoreboard events carry season.type; schedule events carry seasonType.type.
    """
    season = event.get("season", {})
    year = season.get("year")
    stype = season.get("type")
    if stype is None:
        stype = event.get("seasonType", {}).get("type")
    num = event.get("week", {}).get("number")
    if not year:
        return None
    if stype == 1 and num:
        return f"{year}/preseason-week{num}"
    if stype == 2 and num:
        return f"{year}/week{num}"  # no hyphen: pts uses week1, not week-1
    if stype == 3 and num in _NFL_PLAYOFF:
        return f"{year}/{_NFL_PLAYOFF[num]}"
    return None


def _pts_url(league, when_local, away_abbr, home_abbr, event=None):
    away, home = _pts_slug(league, away_abbr), _pts_slug(league, home_abbr)
    if league == "nfl":
        # plaintextsports keys NFL by week, not date; fall back to the index
        seg = _nfl_week_seg(event or {})
        return (f"https://plaintextsports.com/nfl/{seg}/{away}-{home}"
                if seg else "https://plaintextsports.com/nfl/")
    return (f"https://plaintextsports.com/{league}/{when_local:%Y-%m-%d}/"
            f"{away}-{home}")


def _sides(comp):
    competitors = comp.get("competitors", [])
    if len(competitors) != 2:
        return None, None
    away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[0])
    home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[1])
    return away, home


def _game_entry(league, event, recaps):
    """Structured finished/in-progress Pittsburgh game; None otherwise.

    Returns {date, result, url, recap}; the result string is the clickable
    matchup text (the URL is hidden behind it in the rendered HTML).
    """
    comp = event["competitions"][0]
    away, home = _sides(comp)
    if away is None:
        return None
    away_abbr = away["team"].get("abbreviation", "")
    home_abbr = home["team"].get("abbreviation", "")
    if TEAM_ABBR not in (away_abbr, home_abbr):
        return None
    status = event.get("status", {}).get("type", {})
    state = status.get("state", "")
    if state == "pre":
        return None  # upcoming games come from the schedule endpoint instead

    when = _parse_when(event["date"])
    away_name = away["team"].get("shortDisplayName", "?")
    home_name = home["team"].get("shortDisplayName", "?")
    detail = status.get("shortDetail") or status.get("detail") or ""
    entry = {"date": f"{when:%a %b} {when.day}",  # e.g. "Fri Jun 12"
             "url": _pts_url(league, when, away_abbr, home_abbr, event),
             "recap": ""}

    if state == "post" and not status.get("completed", True):
        # postponed/canceled/suspended games carry state=post with 0-0 scores
        entry["result"] = f"{away_name} @ {home_name} · {detail or 'Postponed'}"
        return entry
    if state == "post":
        d = detail.replace("Final", "").strip("/ ")
        detail = "Final" + (f" ({d})" if d else "")
    elif state == "in":
        # The site is static and refreshes a few times a day, so a live score is
        # a frozen snapshot. Label it so a mid-game freeze reads honestly.
        detail = f"{detail} (in progress at last update)".strip()
    entry["result"] = (f"{away_name} {away.get('score', '?')} · "
                       f"{home_name} {home.get('score', '?')} · {detail}")
    recap = (comp.get("headlines") or [{}])[0].get("shortLinkText", "")
    if recap:
        recaps.append(recap)
        entry["recap"] = recap
    return entry


def _schedule_next(sport, league, now_utc):
    """Earliest upcoming game within the horizon, from the team schedule endpoint.

    The teams endpoint's nextEvent field is unreliable (it returns the most
    recent completed game), so query the full schedule instead.
    """
    sched = _espn_json(f"/{sport}/{league}/teams/{TEAM_ABBR.lower()}/schedule")
    horizon = now_utc + NEXT_GAME_HORIZON
    best = None
    for event in sched.get("events", []):
        comp = (event.get("competitions") or [{}])[0]
        state = comp.get("status", {}).get("type", {}).get("state")
        if state and state != "pre":
            continue  # skip postponed/suspended/done rows that keep a future date
        try:
            when = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
        except (KeyError, ValueError, AttributeError):
            continue
        if now_utc < when <= horizon and (best is None or when < best[0]):
            best = (when, event)
    return best[1] if best else None


def _next_entry(league, event):
    """Structured next game {matchup, when, url}; None if unparseable."""
    comp = (event.get("competitions") or [{}])[0]
    away, home = _sides(comp)
    if away is None:
        return None
    away_team = away.get("team") or {}
    home_team = home.get("team") or {}
    try:
        when = _parse_when(event["date"])
    except (KeyError, ValueError):
        return None
    return {
        "matchup": f"{away_team.get('shortDisplayName', '?')} @ "
                   f"{home_team.get('shortDisplayName', '?')}",
        "when": f"{when:%a %b} {when.day}, {when:%-I:%M %p}",  # e.g. "Sat Jun 14"
        "url": _pts_url(league, when, away_team.get("abbreviation", ""),
                        home_team.get("abbreviation", ""), event),
    }


def _team_block(sport, league, now_local, now_utc, errors):
    """Structured block {team, record, games[], next} or None (off-season).

    Team news is not taken from ESPN (its news endpoint returned stale, often
    contradictory blurbs); it comes from the model-summarized "Around the Teams"
    section instead. Partial failures (a scoreboard date, the schedule) are
    appended to `errors` so the run can report them.
    """
    blob = _espn_json(f"/{sport}/{league}/teams/{TEAM_ABBR.lower()}")["team"]
    name = blob.get("shortDisplayName", "Pittsburgh")
    record = blob.get("record", {}).get("items", [{}])[0].get("summary", "")

    games, recaps, seen = [], [], set()
    dates = [(now_local - timedelta(days=1)).strftime("%Y%m%d"),
             now_local.strftime("%Y%m%d")]
    for date in dates:
        try:
            board = _espn_json(f"/{sport}/{league}/scoreboard?dates={date}")
        except Exception as exc:
            print(f"  sports: {league} {date} unavailable: {exc}")
            errors.append(f"{league} scoreboard {date}: {_reason(exc)}")
            continue
        for event in board.get("events", []):
            if event.get("id") in seen:
                continue
            try:
                entry = _game_entry(league, event, recaps)
            except Exception:
                continue  # one malformed event must not sink the section
            if entry:
                seen.add(event.get("id"))
                games.append(entry)

    try:  # the cosmetic tail must not discard already-built scores
        nxt = _schedule_next(sport, league, now_utc)
        next_entry = _next_entry(league, nxt) if nxt else None
    except Exception as exc:
        print(f"  sports: {league} schedule unavailable: {exc}")
        errors.append(f"{league} schedule: {_reason(exc)}")
        next_entry = None
    if not games and not next_entry:
        return None  # off-season: skip the team entirely

    return {"team": name, "record": record, "games": games, "next": next_entry,
            "source": "ESPN"}


# ------------------------------------------------ plaintextsports fallback

PTS_HEADERS = {"User-Agent": USER_AGENT, "Accept": "text/html"}


def _pts_page(league, now_local):
    """(html, url) of the team's current-season page on plaintextsports.com.

    A new season's page appears some weeks before it starts, so a 404 on the
    first candidate path falls through to the previous season's (which then
    parses as off-season). Any other HTTP error is raised as "HTTP <code>".
    """
    url = None
    for season in pts.season_paths(league, now_local):
        url = pts.team_page_url(league, season)
        try:
            return _get_text(url, headers=PTS_HEADERS), url
        except urllib.error.HTTPError as exc:
            err = _http_error(f"plaintextsports {url}", exc)
            if exc.code != 404:
                raise err from None
    raise RuntimeError("HTTP 404 (no season page)")


def _pts_block(league, now_local):
    page, url = _pts_page(league, now_local)
    return pts.parse_team_page(page, league, now_local, page_url=url)


def sports_blocks(errors=None, notes=None):
    """Per-team structured blocks for the Pirates, Steelers, and Penguins.

    ESPN is asked first; when it fails for a league, in whole or in part, that
    league's plaintextsports.com team page is parsed instead, and whatever
    ESPN did return is kept when the fallback fails or shows nothing current.
    Never raises. Unrecovered failures go to `errors` as "league: reason"
    strings and recoveries (plus stale-page and markup-drift warnings) to
    `notes`, so both the outage and the source actually used are visible in
    the published feed-health report rather than only in the container log.
    Each block carries "source": "ESPN" or "plaintextsports".
    """
    errors = [] if errors is None else errors
    notes = [] if notes is None else notes
    now_local = datetime.now(TZ)
    now_utc = datetime.now(timezone.utc)
    blocks = []
    for sport, league in LEAGUES:
        espn_errors, block = [], None
        try:
            block = _team_block(sport, league, now_local, now_utc, espn_errors)
        except Exception as exc:
            print(f"  sports: {league} ESPN unavailable: {exc}")
            espn_errors.append(f"{league}: {_reason(exc)}")
        if not espn_errors:
            if block:
                blocks.append(block)
            continue
        try:
            fallback = _pts_block(league, now_local)
        except Exception as exc:
            print(f"  sports: {league} plaintextsports unavailable: {exc}")
            errors.extend(espn_errors)
            errors.append(f"{league} plaintextsports: {_reason(exc)}")
            if block:
                blocks.append(block)  # whatever ESPN did return beats nothing
            continue
        notes.append(f"{league}: ESPN failed ({'; '.join(espn_errors)}); "
                     f"used plaintextsports")
        notes.extend(_pts_health(league, fallback, now_local))
        if fallback and (fallback.get("games") or fallback.get("next")):
            blocks.append(fallback)
        elif block:
            blocks.append(block)  # partial ESPN data beats an empty fallback
    return blocks


PTS_STALE = timedelta(hours=36)  # NFL/NHL pages are republished daily


def _pts_health(league, fallback, now_local):
    """Notes about a parsed plaintextsports page worth publishing: rows the
    parser did not understand (markup drift) and a page whose last publish is
    older than a day and a half (a missed republish, or last season's page)."""
    notes = []
    if not fallback:
        return notes
    if fallback.get("unparsed"):
        notes.append(f"{league}: {fallback['unparsed']} plaintextsports rows not understood")
    try:
        as_of = datetime.fromisoformat(fallback["as_of"]) if fallback.get("as_of") else None
    except (ValueError, TypeError):
        as_of = None
    if as_of and now_local - as_of > PTS_STALE:
        notes.append(f"{league}: plaintextsports page last published {as_of:%b} {as_of.day}")
    return notes


if __name__ == "__main__":
    print("\n".join(weather_lines()))
    print()
    _errors, _notes = [], []
    print(json.dumps(sports_blocks(_errors, _notes), indent=2, ensure_ascii=False))
    if _notes:
        print("\nnotes:\n  " + "\n  ".join(_notes))
    if _errors:
        print("\nerrors:\n  " + "\n  ".join(_errors))
