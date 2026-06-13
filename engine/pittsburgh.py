"""Pittsburgh weather (National Weather Service) and pro sports scores (ESPN),
formatted as plain-text lines in the spirit of plaintextsports.com.
Stdlib only, no API keys.
"""

import json
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TIMEOUT = 20
TZ = ZoneInfo("America/New_York")
USER_AGENT = "infosecfollow/1.0 (https://infosecfollow.com)"
NWS_POINT = "https://api.weather.gov/points/40.4406,-79.9959"  # downtown Pittsburgh
LEAGUES = [("baseball", "mlb"), ("football", "nfl"), ("hockey", "nhl")]
TEAM_ABBR = "PIT"


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


def _format_game(event, today_local):
    comp = event["competitions"][0]
    competitors = comp.get("competitors", [])
    if len(competitors) != 2:
        return None
    away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[0])
    home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[1])
    if TEAM_ABBR not in (away["team"].get("abbreviation"), home["team"].get("abbreviation")):
        return None

    status = event.get("status", {}).get("type", {})
    state = status.get("state", "")
    away_name = away["team"].get("shortDisplayName", "?")
    home_name = home["team"].get("shortDisplayName", "?")

    if state == "pre":
        start = datetime.fromisoformat(event["date"].replace("Z", "+00:00")).astimezone(TZ)
        day = "Today" if start.date() == today_local else start.strftime("%a %b %-d")
        return f"{away_name} @ {home_name}, {day} {start.strftime('%-I:%M %p')}"
    detail = status.get("shortDetail") or status.get("detail") or ""
    if state == "post":
        if not status.get("completed", True):
            # postponed/canceled/suspended games carry state=post with 0-0 scores
            return f"{away_name} @ {home_name}, {detail or 'Postponed'}"
        detail = "Final" + (f" ({d})" if (d := detail.replace("Final", "").strip("/ ")) else "")
        return f"{away_name} {away.get('score', '?')}  {home_name} {home.get('score', '?')}  {detail}"
    return f"{away_name} {away.get('score', '?')}  {home_name} {home.get('score', '?')}  {detail}"


def sports_lines():
    """Pittsburgh pro games from yesterday and today across MLB/NFL/NHL."""
    now_local = datetime.now(TZ)
    dates = [(now_local - timedelta(days=1)).strftime("%Y%m%d"),
             now_local.strftime("%Y%m%d")]
    lines, seen = [], set()
    for sport, league in LEAGUES:
        for date in dates:
            try:
                board = _get_json(
                    "https://site.api.espn.com/apis/site/v2/sports/"
                    f"{sport}/{league}/scoreboard?dates={date}")
            except Exception as exc:
                print(f"  sports: {league} {date} unavailable: {str(exc)[:120]}")
                continue
            for event in board.get("events", []):
                if event.get("id") in seen:
                    continue
                try:
                    line = _format_game(event, now_local.date())
                except Exception:
                    continue  # one malformed event must not sink the section
                if line:
                    seen.add(event.get("id"))
                    lines.append(line)
    return lines


if __name__ == "__main__":
    print("\n".join(weather_lines()))
    print()
    print("\n".join(sports_lines()) or "no Pittsburgh games yesterday or today")
