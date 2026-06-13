"""Pittsburgh weather (National Weather Service) and pro sports (ESPN),
formatted as plain-text blocks in the spirit of plaintextsports.com, with
game links into plaintextsports.com. Stdlib only, no API keys.
"""

import json
import textwrap
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TIMEOUT = 20
TZ = ZoneInfo("America/New_York")
USER_AGENT = "infosecfollow/1.0 (https://infosecfollow.com)"
NWS_POINT = "https://api.weather.gov/points/40.4406,-79.9959"  # downtown Pittsburgh
ESPN = "https://site.api.espn.com/apis/site/v2/sports"
LEAGUES = [("baseball", "mlb"), ("football", "nfl"), ("hockey", "nhl")]
TEAM_ABBR = "PIT"
PROSE_WIDTH = 58            # wrap recap/headline prose inside the block
NEXT_GAME_HORIZON = timedelta(days=10)
NEWS_MAX_AGE = timedelta(hours=48)


def _get_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
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


def _pts_url(league, when_local, away_abbr, home_abbr):
    return (f"https://plaintextsports.com/{league}/{when_local:%Y-%m-%d}/"
            f"{away_abbr.lower()}-{home_abbr.lower()}")


def _wrap_prose(text, indent="  "):
    return textwrap.wrap(text, width=PROSE_WIDTH, initial_indent=indent,
                         subsequent_indent=indent)


def _sides(comp):
    competitors = comp.get("competitors", [])
    if len(competitors) != 2:
        return None, None
    away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[0])
    home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[1])
    return away, home


def _game_lines(league, event, recaps):
    """Lines for a finished or in-progress Pittsburgh game; None otherwise."""
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
        return None  # upcoming games come from the team's nextEvent instead

    when = _parse_when(event["date"])
    date_str = f"{when:%b} {when.day}"
    away_name = away["team"].get("shortDisplayName", "?")
    home_name = home["team"].get("shortDisplayName", "?")
    detail = status.get("shortDetail") or status.get("detail") or ""

    if state == "post" and not status.get("completed", True):
        # postponed/canceled/suspended games carry state=post with 0-0 scores
        return [f"{date_str}: {away_name} @ {home_name}  {detail or 'Postponed'}"]
    if state == "post":
        d = detail.replace("Final", "").strip("/ ")
        detail = "Final" + (f" ({d})" if d else "")
    lines = [f"{date_str}: {away_name} {away.get('score', '?')}  "
             f"{home_name} {home.get('score', '?')}  {detail}"]
    recap = (comp.get("headlines") or [{}])[0].get("shortLinkText", "")
    if recap:
        recaps.append(recap)
        lines += _wrap_prose(recap)
    lines.append(f"  {_pts_url(league, when, away_abbr, home_abbr)}")
    return lines


def _next_event_lines(league, blob, now_local):
    for event in blob.get("nextEvent", []):
        comp = (event.get("competitions") or [{}])[0]
        state = comp.get("status", {}).get("type", {}).get("state", "pre")
        if state != "pre":
            continue  # in progress or done: the scoreboard pass shows it
        try:
            when = _parse_when(event["date"])
        except (KeyError, ValueError):
            continue
        if when - now_local > NEXT_GAME_HORIZON:
            continue
        away, home = _sides(comp)
        if away is None:
            continue
        venue = comp.get("venue", {})
        place = ", ".join(x for x in (venue.get("fullName"),
                                      venue.get("address", {}).get("city")) if x)
        lines = [f"Next: {away['team'].get('shortDisplayName', '?')} @ "
                 f"{home['team'].get('shortDisplayName', '?')}  "
                 f"{when:%b} {when.day}, {when:%-I:%M %p}"]
        if place:
            lines.append(f"  {place}")
        lines.append(f"  {_pts_url(league, when, away['team'].get('abbreviation', ''), home['team'].get('abbreviation', ''))}")
        return lines
    return []


def _team_news(sport, league, now_utc, recaps):
    """Up to two fresh team headlines, minus the game recap already shown."""
    try:
        articles = _get_json(
            f"{ESPN}/{sport}/{league}/news?team={TEAM_ABBR.lower()}&limit=6"
        ).get("articles", [])
    except Exception:
        return []
    headlines = []
    for article in articles:
        headline = article.get("headline", "").strip()
        try:
            published = datetime.fromisoformat(
                article.get("published", "").replace("Z", "+00:00"))
        except ValueError:
            continue
        if not headline or now_utc - published > NEWS_MAX_AGE:
            continue
        if any(headline in r or r in headline for r in recaps):
            continue
        headlines.append(headline)
        if len(headlines) == 2:
            break
    return headlines


def _team_block(sport, league, now_local, now_utc):
    blob = _get_json(f"{ESPN}/{sport}/{league}/teams/{TEAM_ABBR.lower()}")["team"]
    name = blob.get("shortDisplayName", "Pittsburgh")
    record = blob.get("record", {}).get("items", [{}])[0].get("summary", "")

    game_lines, recaps, seen = [], [], set()
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
                lines = _game_lines(league, event, recaps)
            except Exception:
                continue  # one malformed event must not sink the section
            if lines:
                seen.add(event.get("id"))
                game_lines += lines

    next_lines = _next_event_lines(league, blob, now_local)
    if not game_lines and not next_lines:
        return []  # off-season: skip the team entirely

    block = [f"{name.upper()} ({record})" if record else name.upper()]
    block += game_lines + next_lines
    news = _team_news(sport, league, now_utc, recaps)
    if news:
        block.append("Headlines:")
        for headline in news:
            block += _wrap_prose(headline)
    return block


def sports_lines():
    """Per-team plaintextsports-style blocks for the Pirates, Steelers, Penguins."""
    now_local = datetime.now(TZ)
    now_utc = datetime.now(timezone.utc)
    lines = []
    for sport, league in LEAGUES:
        try:
            block = _team_block(sport, league, now_local, now_utc)
        except Exception as exc:
            print(f"  sports: {league} unavailable: {str(exc)[:120]}")
            continue
        if block:
            if lines:
                lines.append("")
            lines += block
    return lines


if __name__ == "__main__":
    print("\n".join(weather_lines()))
    print()
    print("\n".join(sports_lines()) or "no Pittsburgh games in the window")
