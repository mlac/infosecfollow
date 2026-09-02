"""Parser for plaintextsports.com team pages: the fallback scoreboard source
when ESPN's site API is unreachable (it has answered 403 to the container
since 2026-08-04).

The site renders a team's season as one pre-formatted text page, one game
per line, for example (MLB, tags abbreviated):

  G139:   9/1 v <a href="/mlb/2026/teams/san-francisco-giants">Giants</a>
          <a class="text-fg game-nav" href="/mlb/2026-09-01/sf-pit">
          <span class="text-green">W</span> 13-12</a>      68-71
  G140: We   9/2 <time datetime="2026-09-02T22:40:00Z"> 6:40 PM</time> v
          <span class="text-gray"> 57-82</span> <a ...>Giants</a>
  W9:  <span class="text-gray italic">               bye</span>          (NFL)

Finished games carry W/L and the score winner-first ("L 4-1" is a 4-1 loss),
plus "/11", "/OT" or "/SO" for extras; upcoming games carry a <time> with the
UTC start. The MLB page is rendered live; NFL and NHL pages are republished
about once a day, so an evening run can see a game that has kicked off but
has no result yet. Games link to "/{league}/{date}/{away}-{home}" (NFL:
"/nfl/{year}/{week}/{away}-{home}"); team abbreviations are learned from
those links so upcoming games can be linked too.

The page is not XML (bare text, unclosed tags), so it is parsed with regular
expressions line by line. Stdlib only. Everything returned is third-party
text and must be sanitized by the renderer (generate._clean_sports).
"""

import html
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")
SITE = "https://plaintextsports.com"
SOURCE = "plaintextsports"
TEAMS = {"mlb": "pittsburgh-pirates", "nfl": "pittsburgh-steelers",
         "nhl": "pittsburgh-penguins"}
NEXT_GAME_HORIZON = timedelta(days=15)  # same horizon as the ESPN path

_TITLE = re.compile(r"<title>\s*(?P<start>\d{4})(?:-(?P<end>\d{4}))?\s+(?P<team>[^<]+?)\s*</title>")
_RECORD = re.compile(r'<a class="text-gray" href="/[a-z]+/[^"]*/standings">(?P<record>[^<]+)</a>')
_AS_OF = re.compile(r'<time datetime="(?P<iso>[^"]+)"[^>]*(?:data-format="publish-time"|id=data-loaded)')
# "G139:   9/1 v", "G140: We   9/2 <time ...> 6:40 PM</time> v", "W1:   9/13 vs",
# "W16:   TBD vs"; the day-of-week abbreviation and the <time> are optional.
_ROW = re.compile(
    r"(?P<id>[GWP]\d+):\s*(?:[A-Z][a-z]\s+)?(?:(?P<mon>\d{1,2})/(?P<day>\d{1,2})|TBD)\s+"
    r"(?:<time[^>]*>[^<]*</time>\s+)?(?P<venue>vs|v|at|@)\s")
_OPP = re.compile(r'<a class="text-fg" href="/[a-z]+/[^"]+/teams/(?P<slug>[^"/]+)">(?P<name>[^<]+)</a>')
_GAME = re.compile(r'<a class="text-fg (?P<cls>game-nav|live-nav)" href="(?P<href>[^"]+)">(?P<inner>.*?)</a>')
_RESULT = re.compile(r'<span class="[^"]*">(?P<wl>[WLT])</span>\s*(?P<first>\d+)-(?P<second>\d+)'
                     r'(?:/(?P<extra>[A-Za-z0-9]+))?')
_TIME = re.compile(r'<time[^>]*datetime="(?P<iso>[^"]+)"')
_HREF_DATE = re.compile(r"^/[a-z]+/(?P<date>\d{4}-\d{2}-\d{2})/(?P<away>[a-z0-9]+)-(?P<home>[a-z0-9]+)$")
_HREF_OK = re.compile(r"^/[a-z0-9][a-z0-9/_-]*$")
_TAG = re.compile(r"<[^>]+>")


def season_paths(league, now_local):
    """Season path segments to try, most likely first.

    NHL seasons are "2025-2026"; MLB and NFL pages are keyed by the calendar
    year the season starts in, so an NFL January game still lives on the
    previous year's page. The second candidate covers the weeks before a new
    season's page exists (a 404 on the first).
    """
    y, m = now_local.year, now_local.month
    if league == "nhl":
        this, last = f"{y}-{y + 1}", f"{y - 1}-{y}"
        return [this, last] if m >= 7 else [last, this]
    return [str(y - 1), str(y)] if m <= 2 else [str(y), str(y - 1)]


def team_page_url(league, season):
    return f"{SITE}/{league}/{season}/teams/{TEAMS[league]}"


def _parse_iso(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ)
    except (ValueError, AttributeError):
        return None


def _text(fragment):
    return " ".join(html.unescape(_TAG.sub(" ", fragment)).split())


def _resolve_date(mon, day, season_start, now_local):
    """Row dates have no year: pick, from the season's two calendar years, the
    one that puts the game nearest to now (an NFL "1/3" in the 2026 season is
    2027-01-03)."""
    best = None
    for year in (season_start, season_start + 1):
        try:
            when = datetime(year, mon, day, tzinfo=TZ)
        except ValueError:
            continue
        gap = abs((when.date() - now_local.date()).days)
        if best is None or gap < best[0]:
            best = (gap, when)
    return best[1] if best else None


def _game_url(href, league):
    if href and _HREF_OK.match(href):
        return SITE + href
    return None


def parse_team_page(page, league, now_local, page_url=None):
    """Structured block {team, record, games[], next, source} or None when the
    page holds nothing current (off-season, or unparseable).

    `games` are finished, live, or started-but-unposted games dated yesterday
    or today (local); `next` is the earliest upcoming game inside
    NEXT_GAME_HORIZON. The shapes match pittsburgh._team_block so the
    renderers cannot tell the two sources apart.
    """
    if not isinstance(page, str):
        return None
    title = _TITLE.search(page)
    if not title:
        return None
    season_start = int(title.group("start"))
    full_name = _text(title.group("team"))
    team = re.sub(r"^Pittsburgh\s+", "", full_name) or full_name
    record_m = _RECORD.search(page)
    record = _text(record_m.group("record")) if record_m else ""
    as_of_m = _AS_OF.search(page)
    as_of = _parse_iso(as_of_m.group("iso")) if as_of_m else None
    fallback_url = page_url or team_page_url(league, season_paths(league, now_local)[0])

    today = now_local.date()
    current = {today, today - timedelta(days=1)}
    horizon = now_local + NEXT_GAME_HORIZON
    abbrs = {}          # opponent slug -> plaintextsports abbreviation, learned from links
    rows = []
    seen = set()
    for line in page.splitlines():
        m = _ROW.search(line)
        if not m:
            continue
        opp = _OPP.search(line, m.end())
        if not opp:
            continue  # a bye or a placeholder row
        game = _GAME.search(line, m.end())
        href = game.group("href") if game else ""
        # MLB pages list the current series twice and NHL pages list playoff
        # games both under the round and under the month, with different ids.
        key = href or (m.group("id"), m.group("mon"), m.group("day"), opp.group("slug"))
        if key in seen:
            continue
        seen.add(key)
        href_date = _HREF_DATE.match(href) if href else None
        if href_date:
            other = [a for a in (href_date.group("away"), href_date.group("home")) if a != "pit"]
            if len(other) == 1:
                abbrs.setdefault(opp.group("slug"), other[0])
        rows.append((m, opp, game, href, href_date, line))

    games, upcoming = [], []
    for m, opp, game, href, href_date, line in rows:
        pit_home = m.group("venue") in ("v", "vs")
        opp_name = _text(opp.group("name"))
        away, home = (opp_name, team) if pit_home else (team, opp_name)
        result = _RESULT.search(game.group("inner")) if game else None
        start_m = _TIME.search(line)
        start = _parse_iso(start_m.group("iso")) if start_m else None

        if result:  # finished
            if href_date:
                when = _parse_iso(href_date.group("date") + "T12:00:00+00:00")
            elif m.group("mon"):
                when = _resolve_date(int(m.group("mon")), int(m.group("day")), season_start, now_local)
            else:
                when = None
            if when is None or when.date() not in current:
                continue
            first, second = result.group("first"), result.group("second")
            if result.group("wl") == "L":
                opp_score, pit_score = first, second
            else:
                pit_score, opp_score = first, second
            away_score, home_score = (opp_score, pit_score) if pit_home else (pit_score, opp_score)
            extra = result.group("extra")
            detail = "Final" + (f" ({extra})" if extra else "")
            games.append((when, {
                "date": f"{when:%a %b} {when.day}",
                "result": f"{away} {away_score} · {home} {home_score} · {detail}",
                "url": _game_url(href, league) or fallback_url,
                "recap": ""}))
        elif game and start is None:  # live (live-nav) or a status such as PPD
            when = _parse_iso(href_date.group("date") + "T12:00:00+00:00") if href_date else None
            if when is None and m.group("mon"):
                when = _resolve_date(int(m.group("mon")), int(m.group("day")), season_start, now_local)
            if when is None or when.date() not in current:
                continue
            status = _text(game.group("inner")) or "in progress"
            if game.group("cls") == "live-nav" or re.search(r"\d+-\d+", status):
                status = f"{status} (in progress at last update)"
            games.append((when, {
                "date": f"{when:%a %b} {when.day}",
                "result": f"{away} @ {home} · {status}",
                "url": _game_url(href, league) or fallback_url,
                "recap": ""}))
        elif start is not None:  # scheduled
            if start > now_local:
                if start <= horizon:
                    upcoming.append((start, away, home, opp.group("slug"), href))
            elif start.date() in current:
                # NFL/NHL pages are republished daily, so a game that kicked off
                # after the last publish still shows as scheduled.
                status = f"started {start:%-I:%M %p}, result not posted"
                if as_of:
                    status += f" as of the {as_of:%-I:%M %p} page update"
                games.append((start, {
                    "date": f"{start:%a %b} {start.day}",
                    "result": f"{away} @ {home} · {status}",
                    "url": _game_url(href, league) or fallback_url,
                    "recap": ""}))

    games.sort(key=lambda g: g[0])
    nxt = None
    if upcoming:
        upcoming.sort(key=lambda u: u[0])
        start, away, home, slug, href = upcoming[0]
        url = _game_url(href, league)
        if not url and league != "nfl" and slug in abbrs:
            pit_home = home == team
            away_abbr, home_abbr = ("pit", abbrs[slug]) if not pit_home else (abbrs[slug], "pit")
            url = f"{SITE}/{league}/{start:%Y-%m-%d}/{away_abbr}-{home_abbr}"
        nxt = {"matchup": f"{away} @ {home}",
               "when": f"{start:%a %b} {start.day}, {start:%-I:%M %p}",
               "url": url or fallback_url}

    if not games and not nxt:
        return None
    return {"team": team, "record": record, "games": [g for _, g in games],
            "next": nxt, "source": SOURCE}
