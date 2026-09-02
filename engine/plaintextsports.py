"""Parser for plaintextsports.com team pages: the fallback scoreboard source
when ESPN's site API is unreachable (it has answered 403 to the container
since 2026-08-04).

The site renders a team's season as one pre-formatted text page, one game
per row, for example (MLB, tags abbreviated):

  G139:   9/1 v <a href="/mlb/2026/teams/san-francisco-giants">Giants</a>
          <a class="text-fg game-nav" href="/mlb/2026-09-01/sf-pit">
          <span class="text-green">W</span> 13-12</a>      68-71
  G140: We   9/2 <time datetime="2026-09-02T22:40:00Z"> 6:40 PM</time> v
          <span class="text-gray"> 57-82</span> <a ...>Giants</a>
  G97:   7/10 v <a ...>Brewers</a> <a class="text-gray" href="...">postponed</a>
  W9:  <span class="text-gray italic">               bye</span>          (NFL)

Finished games carry W/L and the score winner-first ("L 4-1" is a 4-1 loss),
plus "/11", "/OT" or "/SO" for extras; upcoming games carry a <time> with the
UTC start; live games use a "live-nav" link. The MLB page is rendered live;
NFL and NHL pages are republished about once a day, so an evening run can
see a game that has kicked off but has no result yet. Games link to
"/{league}/{date}/{away}-{home}" (NFL: "/nfl/{year}/{week}/{away}-{home}");
team abbreviations are learned from those links so upcoming games can be
linked too. Two rows can share one physical line (the MLB month listing puts
each series' first game on the previous series' last line), so lines are
split at row starts before matching.

The page is not XML (bare text, unclosed tags), so it is parsed with
regular expressions. Every quantifier is bounded and rows and line lengths
are capped, because the page is third-party input and the parser runs
inside the whole-run time budget. Everything returned is third-party text
and must be sanitized by the renderer (generate._clean_sports). Stdlib only.
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
MAX_LINE = 20_000    # a real row line is under 1 KB; two rows share ~600 bytes
MAX_ROWS = 400       # a full MLB season with its twice-listed series is ~200
STATUS_WORDS = ("postponed", "suspended", "canceled", "cancelled", "delayed", "ppd")

_TITLE = re.compile(r"<title>\s{0,20}(?P<start>\d{4})(?:-(?P<end>\d{4}))?\s{1,20}"
                    r"(?P<team>[^<]{1,120})</title>")
_RECORD = re.compile(r'<a class="text-gray" href="/[a-z]{2,5}/[^"]{1,40}/standings">'
                     r'(?P<record>[^<]{1,60})</a>')
_AS_OF = re.compile(r'<time datetime="(?P<iso>[^"]{1,40})"[^>]{0,200}'
                    r'(?:data-format="publish-time"|id=data-loaded)')
# "G139:   9/1 v", "G140: We   9/2 <time ...> 6:40 PM</time> v", "W1:   9/13 vs",
# "W16:   TBD vs"; the day-of-week abbreviation and the <time> are optional.
_ROW = re.compile(r"(?P<id>[A-Z]{1,4}\d{0,4}):\s{0,40}(?:[A-Z][a-z]\s{1,20})?"
                  r"(?:(?P<mon>\d{1,2})/(?P<day>\d{1,2})|TBD)\s{1,20}"
                  r"(?:<time[^>]{0,300}>[^<]{0,40}</time>\s{1,20})?(?P<venue>vs|v|at|@)\s")
_OPP = re.compile(r'<a class="text-fg" href="/[a-z]{2,5}/[^"]{1,60}/teams/(?P<slug>[^"/]{1,80})">'
                  r'(?P<name>[^<]{1,80})</a>')
_GAME = re.compile(r'<a class="text-fg (?P<cls>game-nav|live-nav)" href="(?P<href>[^"]{1,300})">'
                   r'(?P<inner>[^\n]{0,400}?)</a>')
_STATUS = re.compile(r'<a class="text-gray" href="(?P<href>[^"]{1,300})">\s{0,20}'
                     r'(?P<text>[A-Za-z][A-Za-z .]{0,30}?)\s{0,20}</a>')
_RESULT = re.compile(r'<span class="[^"]{0,40}">(?P<wl>[WLT])</span>\s{0,20}'
                     r'(?P<first>\d{1,3})-(?P<second>\d{1,3})(?:/(?P<extra>[A-Za-z0-9]{1,6}))?')
_TIME = re.compile(r'<time[^>]{0,300}datetime="(?P<iso>[^"]{1,40})"')
_TIME_TAG = re.compile(r"<time[^>]{0,300}>[^<]{0,40}</time>")
_HREF_DATE = re.compile(r"^/[a-z]{2,5}/(?P<date>\d{4}-\d{2}-\d{2})/"
                        r"(?P<away>[a-z0-9]{1,6})-(?P<home>[a-z0-9]{1,6})$")
_HREF_OK = re.compile(r"^/[a-z0-9][a-z0-9/_-]{0,200}$")
_TAG = re.compile(r"<[^>]{0,1000}>")


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
    except (ValueError, OverflowError, AttributeError):
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


def _game_url(href):
    if href and _HREF_OK.match(href):
        return SITE + href
    return None


def _rows(page):
    """(row match, opponent match, game-link match, status match, segment) per
    game row, with each physical line split at row starts so a second row on
    the same line is neither lost nor searched into."""
    rows = []
    for line in page.splitlines():
        if len(line) > MAX_LINE:
            continue
        starts = list(_ROW.finditer(line))
        for i, m in enumerate(starts):
            end = starts[i + 1].start() if i + 1 < len(starts) else len(line)
            seg = line[m.start():end]
            offset = m.end() - m.start()
            opp = _OPP.search(seg, offset)
            if not opp:
                continue  # a bye or a placeholder row
            game = _GAME.search(seg, offset)
            status = None if game else _STATUS.search(seg, offset)
            if status and status.group("text").strip().lower() not in STATUS_WORDS:
                status = None
            rows.append((m, opp, game, status, seg))
            if len(rows) >= MAX_ROWS:
                return rows
    return rows


def _game_date(href_date, m, season_start, now_local):
    """Local date of a finished/status row: from the game link when it carries
    one (MLB/NHL), else from the row's month/day (NFL)."""
    if href_date:
        return _parse_iso(href_date.group("date") + "T12:00:00+00:00")
    if m.group("mon"):
        return _resolve_date(int(m.group("mon")), int(m.group("day")), season_start, now_local)
    return None


def parse_team_page(page, league, now_local, page_url=None):
    """Structured block {team, record, games[], next, source, as_of, unparsed}
    or None when the page parsed but holds nothing current (off-season).
    Raises ValueError when the text is not a team page at all (a stub or
    redirect page, markup drift), so the caller can report it rather than
    mistake it for the off-season.

    `games` are finished, live, postponed, or started-but-unposted games dated
    yesterday or today (local); `next` is the earliest upcoming game inside
    NEXT_GAME_HORIZON. The shapes match pittsburgh._team_block so the
    renderers cannot tell the two sources apart. A malformed row is skipped,
    never fatal; rows that fit no known shape are counted in `unparsed`.
    """
    if not isinstance(page, str):
        raise ValueError("not a team page (not text)")
    title = _TITLE.search(page)
    if not title:
        raise ValueError("not a team page (no season title)")
    rows = _rows(page)
    if not rows:
        raise ValueError("not a team page (no game rows)")
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
    seen = set()
    games, upcoming = [], []
    unparsed = 0  # rows with an opponent that fit no known shape (markup drift)
    for m, opp, game, status, seg in rows:
        try:
            href = (game or status).group("href") if (game or status) else ""
            href_date = _HREF_DATE.match(href) if href else None
            start_m = _TIME.search(seg)
            start = _parse_iso(start_m.group("iso")) if start_m else None
            # MLB pages list the current series twice and NHL pages list playoff
            # games both under the round and under the month, with different
            # ids: key on the link, else on the row's own content.
            key = href or (m.group("mon"), m.group("day"), opp.group("slug"),
                           start_m.group("iso") if start_m else None)
            if key in seen:
                continue
            seen.add(key)
            if href_date:
                other = [a for a in (href_date.group("away"), href_date.group("home")) if a != "pit"]
                if len(other) == 1:
                    abbrs.setdefault(opp.group("slug"), other[0])

            pit_home = m.group("venue") in ("v", "vs")
            opp_name = _text(opp.group("name"))
            away, home = (opp_name, team) if pit_home else (team, opp_name)
            result = _RESULT.search(game.group("inner")) if game else None
            url = _game_url(href) or fallback_url

            if result:  # finished
                when = _game_date(href_date, m, season_start, now_local)
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
                    "url": url, "recap": ""}))
            elif status:  # postponed, suspended, ...
                when = _game_date(href_date, m, season_start, now_local)
                if when is None or when.date() not in current:
                    continue
                games.append((when, {
                    "date": f"{when:%a %b} {when.day}",
                    "result": f"{away} @ {home} · {status.group('text').strip().capitalize()}",
                    "url": url, "recap": ""}))
            elif game and (game.group("cls") == "live-nav" or start is None):  # live
                when = _game_date(href_date, m, season_start, now_local)
                if when is None or when.date() not in current:
                    continue
                label = _text(_TIME_TAG.sub(" ", game.group("inner"))) or "in progress"
                if game.group("cls") == "live-nav" or re.search(r"\d+-\d+", label):
                    label = f"{label} (in progress at last update)"
                games.append((when, {
                    "date": f"{when:%a %b} {when.day}",
                    "result": f"{away} @ {home} · {label}",
                    "url": url, "recap": ""}))
            elif start is not None:  # scheduled
                if start > now_local:
                    if start <= horizon:
                        upcoming.append((start, away, home, opp.group("slug"), href))
                elif start.date() in current:
                    # NFL/NHL pages are republished daily, so a game that kicked
                    # off after the last publish still shows as scheduled.
                    label = f"started {start:%-I:%M %p}, result not posted"
                    if as_of and as_of.date() != now_local.date():
                        label += (f" as of the {as_of:%a %b} {as_of.day} "
                                  f"{as_of:%-I:%M %p} page update")
                    elif as_of:
                        label += f" as of the {as_of:%-I:%M %p} page update"
                    games.append((start, {
                        "date": f"{start:%a %b} {start.day}",
                        "result": f"{away} @ {home} · {label}",
                        "url": url, "recap": ""}))
            else:
                unparsed += 1
        except Exception:
            continue  # one odd row must not sink the team

    games.sort(key=lambda g: g[0])
    nxt = None
    if upcoming:
        upcoming.sort(key=lambda u: u[0])
        start, away, home, slug, href = upcoming[0]
        url = _game_url(href)
        if not url and league != "nfl" and slug in abbrs:
            pit_home = home == team
            away_abbr, home_abbr = (abbrs[slug], "pit") if pit_home else ("pit", abbrs[slug])
            url = f"{SITE}/{league}/{start:%Y-%m-%d}/{away_abbr}-{home_abbr}"
        nxt = {"matchup": f"{away} @ {home}",
               "when": f"{start:%a %b} {start.day}, {start:%-I:%M %p}",
               "url": url or fallback_url}

    if not games and not nxt and not unparsed:
        return None  # parsed fine, nothing current: off-season
    return {"team": team, "record": record, "games": [g for _, g in games],
            "next": nxt, "source": SOURCE,
            # for the caller's health notes; the renderer's cleaner drops them
            "as_of": as_of.isoformat() if as_of else None, "unparsed": unparsed}
