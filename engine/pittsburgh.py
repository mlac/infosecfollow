"""Pittsburgh weather (National Weather Service) and pro sports (ESPN),
formatted as plain-text blocks in the spirit of plaintextsports.com, with
game links into plaintextsports.com. Stdlib only, no API keys.
"""

import json
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import safefetch

TIMEOUT = 20
TZ = ZoneInfo("America/New_York")
USER_AGENT = "infosecfollow/1.0 (https://infosecfollow.com)"
NWS_POINT = "https://api.weather.gov/points/40.4406,-79.9959"  # downtown Pittsburgh
ESPN = "https://site.api.espn.com/apis/site/v2/sports"
LEAGUES = [("baseball", "mlb"), ("football", "nfl"), ("hockey", "nhl")]
TEAM_ABBR = "PIT"
NEXT_GAME_HORIZON = timedelta(days=15)  # covers an NFL bye week; skips off-season


def _get_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT, "Accept": "application/json"})
    with safefetch.safe_open(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read(4_000_000).decode("utf-8", "replace"))


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
    sched = _get_json(f"{ESPN}/{sport}/{league}/teams/{TEAM_ABBR.lower()}/schedule")
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


def _team_block(sport, league, now_local, now_utc):
    """Structured block {team, record, games[], next, headlines[]} or None.

    headlines is always empty: ESPN's news endpoint returned stale, often
    contradictory blurbs, so team news now comes from the model-summarized
    "Around the Teams" section (beat writers and team podcasts) instead.
    """
    blob = _get_json(f"{ESPN}/{sport}/{league}/teams/{TEAM_ABBR.lower()}")["team"]
    name = blob.get("shortDisplayName", "Pittsburgh")
    record = blob.get("record", {}).get("items", [{}])[0].get("summary", "")

    games, recaps, seen = [], [], set()
    dates = [(now_local - timedelta(days=1)).strftime("%Y%m%d"),
             now_local.strftime("%Y%m%d")]
    for date in dates:
        try:
            board = _get_json(f"{ESPN}/{sport}/{league}/scoreboard?dates={date}")
        except Exception as exc:
            print(f"  sports: {league} {date} unavailable: {str(exc)[:120]}")
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
    except Exception:
        next_entry = None
    if not games and not next_entry:
        return None  # off-season: skip the team entirely

    return {"team": name, "record": record, "games": games,
            "next": next_entry, "headlines": []}


def sports_blocks():
    """Per-team structured blocks for the Pirates, Steelers, and Penguins."""
    now_local = datetime.now(TZ)
    now_utc = datetime.now(timezone.utc)
    blocks = []
    for sport, league in LEAGUES:
        try:
            block = _team_block(sport, league, now_local, now_utc)
        except Exception as exc:
            print(f"  sports: {league} unavailable: {str(exc)[:120]}")
            continue
        if block:
            blocks.append(block)
    return blocks


if __name__ == "__main__":
    import json
    print("\n".join(weather_lines()))
    print()
    print(json.dumps(sports_blocks(), indent=2, ensure_ascii=False))
