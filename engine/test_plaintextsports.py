"""Tests for the plaintextsports.com team-page parser and its use as the
scoreboard fallback when ESPN fails.

The fixtures under testdata/pts/ are real pages saved on 2026-09-02: the MLB
page is rendered live (data loaded 10:34 ET), the NFL page is the daily
snapshot published at 5:00 AM ET, and the NHL page is the 2025-2026 season's,
because the 2026-2027 page did not exist yet. No network is touched.

    python3 -m unittest discover -s engine -p 'test_*.py'
"""

import email.message
import io
import os
import re
import unittest
import urllib.error
from datetime import datetime
from unittest import mock

import generate
import pittsburgh
import plaintextsports as pts

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata", "pts")
SITE = "https://plaintextsports.com"


def fixture(name):
    with open(os.path.join(FIXTURES, name + ".html"), encoding="utf-8") as fh:
        return fh.read()


def at(y, m, d, hour=9, minute=0):
    return datetime(y, m, d, hour, minute, tzinfo=pts.TZ)


def http_error(url, code, server=""):
    headers = email.message.Message()
    if server:
        headers["Server"] = server
    return urllib.error.HTTPError(url, code, "nope", headers, io.BytesIO(b"<html>blocked</html>"))


class TeamPageParsing(unittest.TestCase):
    def test_mlb_live_page_yesterdays_final_and_tonights_game(self):
        block = pts.parse_team_page(fixture("pirates"), "mlb", at(2026, 9, 2, 10, 35))
        self.assertEqual(block["team"], "Pirates")
        self.assertEqual(block["record"], "68-71")
        self.assertEqual(block["source"], "plaintextsports")
        self.assertEqual(block["games"], [{
            "date": "Tue Sep 1", "result": "Giants 12 · Pirates 13 · Final",
            "url": f"{SITE}/mlb/2026-09-01/sf-pit", "recap": ""}])
        # the Giants' abbreviation was learned from the 9/1 game link
        self.assertEqual(block["next"], {
            "matchup": "Giants @ Pirates", "when": "Wed Sep 2, 6:40 PM",
            "url": f"{SITE}/mlb/2026-09-02/sf-pit"})

    def test_score_is_winner_first_and_extra_innings_are_labelled(self):
        block = pts.parse_team_page(fixture("pirates"), "mlb", at(2026, 3, 29))
        self.assertEqual([g["result"] for g in block["games"]],
                         ["Pirates 2 · Mets 4 · Final (11)", "Pirates 4 · Mets 3 · Final (10)"])
        self.assertIsNone(block["next"])  # nothing within 15 days of March 29 on this page

    def test_current_series_listed_twice_yields_one_entry_per_game(self):
        block = pts.parse_team_page(fixture("pirates"), "mlb", at(2026, 8, 29))
        self.assertEqual([g["date"] for g in block["games"]], ["Fri Aug 28", "Sat Aug 29"])
        self.assertEqual(block["games"][0]["result"], "Pirates 1 · Cardinals 4 · Final")
        self.assertEqual(block["next"]["when"], "Wed Sep 2, 6:40 PM")

    def test_nfl_preseason_final_and_next_game_horizon(self):
        block = pts.parse_team_page(fixture("steelers"), "nfl", at(2026, 8, 28))
        self.assertEqual(block["record"], "0-0, T-1st in AFC North")
        self.assertEqual(block["games"], [{
            "date": "Thu Aug 27", "result": "Steelers 27 · Bills 28 · Final",
            "url": f"{SITE}/nfl/2026/preseason-week3/pit-buf", "recap": ""}])
        self.assertIsNone(block["next"])  # week 1 is 16 days out
        block = pts.parse_team_page(fixture("steelers"), "nfl", at(2026, 9, 2))
        self.assertEqual(block["games"], [])
        self.assertEqual(block["next"], {
            "matchup": "Falcons @ Steelers", "when": "Sun Sep 13, 1:00 PM",
            "url": f"{SITE}/nfl/2026/week1/atl-pit"})

    def test_nfl_daily_page_after_kickoff_reports_a_pending_result(self):
        page_url = f"{SITE}/nfl/2026/teams/pittsburgh-steelers"
        block = pts.parse_team_page(fixture("steelers"), "nfl", at(2026, 9, 13, 16, 30),
                                    page_url=page_url)
        self.assertEqual(block["games"], [{
            "date": "Sun Sep 13",
            "result": "Falcons @ Steelers · started 1:00 PM, result not posted "
                      "as of the Wed Sep 2 5:00 AM page update",
            "url": f"{SITE}/nfl/2026/week1/atl-pit", "recap": ""}])
        # same-day publish: the time alone
        page = fixture("steelers").replace("2026-09-02T09:00:00Z", "2026-09-13T09:00:00Z")
        block = pts.parse_team_page(page, "nfl", at(2026, 9, 13, 16, 30), page_url=page_url)
        self.assertTrue(block["games"][0]["result"].endswith("as of the 5:00 AM page update"))
        # week 2 has no game link yet: link the page itself rather than guess
        self.assertEqual(block["next"], {
            "matchup": "Steelers @ Patriots", "when": "Sun Sep 20, 1:00 PM",
            "url": page_url})

    def test_bye_and_tbd_rows_are_ignored(self):
        block = pts.parse_team_page(fixture("steelers"), "nfl", at(2026, 12, 22))
        # W16 (TBD date, year-2100 placeholder time) is skipped; W17 is Jan 3, 2027
        self.assertEqual(block["games"], [])
        self.assertEqual(block["next"]["matchup"], "Steelers @ Titans")
        self.assertEqual(block["next"]["when"], "Sun Jan 3, 1:00 PM")

    def test_nfl_january_final_resolves_to_the_following_year(self):
        page = ('<title>2026 Pittsburgh Steelers</title>'
                '<a class="text-gray" href="/nfl/2026/standings">9-8</a>\n'
                'W17:   1/3 at <span class="text-gray">  7-9 </span>'
                '<a class="text-fg" href="/nfl/2026/teams/tennessee-titans">Titans</a>     '
                '<a class="text-fg game-nav" href="/nfl/2026/week17/pit-ten">'
                '<span class="text-green">W</span> 24-17</a>    9-8\n')
        block = pts.parse_team_page(page, "nfl", at(2027, 1, 4))
        self.assertEqual(block["record"], "9-8")
        self.assertEqual(block["games"], [{
            "date": "Sun Jan 3", "result": "Steelers 24 · Titans 17 · Final",
            "url": f"{SITE}/nfl/2026/week17/pit-ten", "recap": ""}])

    def test_nhl_overtime_shootout_and_playoff_rows(self):
        block = pts.parse_team_page(fixture("penguins"), "nhl", at(2026, 4, 30))
        self.assertEqual(block["record"], "2-4, 102 pts")
        # game 6 is listed under the round and again under April: one entry
        self.assertEqual(block["games"], [{
            "date": "Wed Apr 29", "result": "Penguins 0 · Flyers 1 · Final (OT)",
            "url": f"{SITE}/nhl/2026-04-29/pit-phi", "recap": ""}])
        self.assertIsNone(block["next"])
        block = pts.parse_team_page(fixture("penguins"), "nhl", at(2025, 10, 26))
        self.assertEqual(block["games"][0]["result"],
                         "Blue Jackets 5 · Penguins 4 · Final (SO)")
        self.assertEqual(block["games"][0]["url"], f"{SITE}/nhl/2025-10-25/cbj-pit")

    def test_off_season_page_is_none(self):
        self.assertIsNone(pts.parse_team_page(fixture("penguins"), "nhl", at(2026, 9, 2)))

    def test_two_rows_on_one_physical_line_are_both_parsed(self):
        # the MLB month listing starts each series on the previous series'
        # last line: "...4-3/10</a>     1-2</div><div class="series">G4:    3/30 @ ..."
        block = pts.parse_team_page(fixture("pirates"), "mlb", at(2026, 3, 31))
        self.assertEqual([(g["date"], g["result"], g["url"]) for g in block["games"]], [
            ("Mon Mar 30", "Pirates 0 · Reds 2 · Final", f"{SITE}/mlb/2026-03-30/pit-cin"),
            ("Tue Mar 31", "Pirates 8 · Reds 3 · Final", f"{SITE}/mlb/2026-03-31/pit-cin")])
        # every game link on the page is reachable, not just the first per line
        page = fixture("pirates")
        links = set(re.findall(r'class="text-fg game-nav" href="(/mlb/2026-\d\d-\d\d/[a-z]+-[a-z]+)"', page))
        found = set()
        for mon, day in {(int(a), int(b)) for a, b in re.findall(r"/mlb/2026-(\d\d)-(\d\d)/", page)}:
            after = datetime(2026, mon, day, 9, tzinfo=pts.TZ) + pts.timedelta(days=1)
            for g in pts.parse_team_page(page, "mlb", after)["games"]:
                found.add(g["url"].replace(SITE, ""))
        self.assertEqual(links - found, set())

    def test_postponed_games_are_reported_like_the_espn_path(self):
        block = pts.parse_team_page(fixture("pirates"), "mlb", at(2026, 7, 10, 20))
        self.assertEqual([g["result"] for g in block["games"]],
                         ["Braves 10 · Pirates 5 · Final", "Brewers @ Pirates · Postponed"])
        self.assertEqual(block["games"][1]["url"], f"{SITE}/mlb/2026-07-10/mil-pit")
        block = pts.parse_team_page(fixture("pirates"), "mlb", at(2026, 7, 22))
        self.assertIn("Pirates @ Yankees · Postponed", [g["result"] for g in block["games"]])

    def test_playoff_game_listed_twice_without_a_link_prints_once(self):
        row = ('  4/29 <time datetime="2026-04-29T23:00:00Z"> 7:00 PM</time> @ '
               '<span class="text-gray"> 40-30-12</span> '
               '<a class="text-fg" href="/nhl/2025-2026/teams/philadelphia-flyers">Flyers</a>\n')
        page = ('<title>2025-2026 Pittsburgh Penguins</title>\n'
                '<span title="x">Published: <time datetime="2026-04-29T09:00:00Z" '
                'data-format="publish-time">5:00 AM ET</time></span>\n'
                'G6: We' + row + 'G88: We' + row)
        block = pts.parse_team_page(page, "nhl", at(2026, 4, 29, 19, 32))
        self.assertEqual([g["result"] for g in block["games"]], [
            "Penguins @ Flyers · started 7:00 PM, result not posted as of the 5:00 AM page update"])
        # a doubleheader (two start times) is still two games
        second = row.replace("23:00:00Z", "17:00:00Z")
        block = pts.parse_team_page(page + 'G89: We' + second, "nhl", at(2026, 4, 29, 19, 32))
        self.assertEqual(len(block["games"]), 2)

    def test_live_row_with_an_embedded_time_still_shows_the_live_score(self):
        page = ('<title>2026 Pittsburgh Pirates</title>\n'
                'G140: We   9/2 <time datetime="2026-09-02T22:40:00Z"> 6:40 PM</time> v '
                '<a class="text-fg" href="/mlb/2026/teams/san-francisco-giants">Giants</a> '
                '<a class="text-fg live-nav" href="/mlb/2026-09-02/sf-pit">'
                '<span class="text-red">T5</span> 3-2 <time datetime="2026-09-02T22:40:00Z">'
                '6:40 PM</time></a>\n')
        block = pts.parse_team_page(page, "mlb", at(2026, 9, 2, 19, 32))
        self.assertEqual(block["games"][0]["result"],
                         "Giants @ Pirates · T5 3-2 (in progress at last update)")

    def test_a_malformed_row_never_sinks_the_team(self):
        page = ('<title>2026 Pittsburgh Pirates</title>\n'
                'G1:   9/1 v <a class="text-fg" href="/mlb/2026/teams/x">Giants</a> '
                '<a class="text-fg game-nav" href="/mlb/2026-09-01/sf-pit">'
                '<span class="text-green">W</span> 2-1</a>\n'
                'G2: We   9/2 <time datetime="0001-01-01T00:00:00Z">TBD</time> v '
                '<a class="text-fg" href="/mlb/2026/teams/x">Giants</a>\n'
                'G3: Th   9/3 <time datetime="2026-09-03T16:35:00Z">12:35 PM</time> v '
                '<a class="text-fg" href="/mlb/2026/teams/x">Giants</a>\n')
        block = pts.parse_team_page(page, "mlb", at(2026, 9, 2))
        self.assertEqual(len(block["games"]), 1)
        self.assertEqual(block["next"]["when"], "Thu Sep 3, 12:35 PM")

    def test_hostile_pages_parse_in_bounded_time(self):
        import time
        hostile = [
            "<title>2026 " + " " * 100_000,                          # no closing tag
            '<time datetime="x"' * 50_000,                           # never-closing tags
            "<title>2026 Pittsburgh Pirates</title>\n" + "G1: " * 200_000,
            "<title>2026 Pittsburgh Pirates</title>\n"
            + ('G1:   9/1 v <a class="text-fg" href="/mlb/2026/teams/x">X</a> '
               '<a class="text-fg game-nav" href="' + "a" * 500_000 + '">W 1-0</a>\n'),
            "<title>2026 Pittsburgh Pirates</title>\n" + "\n".join(
                f'G{i}:   9/2 v <a class="text-fg" href="/mlb/2026/teams/t{i}">T{i}</a> '
                f'<a class="text-fg game-nav" href="/mlb/2026-09-02/t{i}-pit">'
                f'<span class="text-green">W</span> 1-0</a>' for i in range(20_000)),
        ]
        started = time.monotonic()
        for page in hostile:
            try:
                block = pts.parse_team_page(page, "mlb", at(2026, 9, 2))
            except ValueError:
                continue
            if block:
                self.assertLessEqual(len(block["games"]), pts.MAX_ROWS)
        self.assertLess(time.monotonic() - started, 5.0)

    def test_rows_of_an_unknown_shape_are_counted_not_dropped_silently(self):
        page = ('<title>2026 Pittsburgh Pirates</title>\n'
                'G1:   9/1 v <a class="text-fg" href="/mlb/2026/teams/x">Giants</a> '
                '<b class="something-new">LIVE 3-2</b>\n')
        block = pts.parse_team_page(page, "mlb", at(2026, 9, 2))
        self.assertEqual((block["games"], block["next"], block["unparsed"]), ([], None, 1))
        # every row on the real pages fits a known shape
        for name, league, now in (("pirates", "mlb", at(2026, 9, 2)),
                                  ("steelers", "nfl", at(2026, 9, 2)),
                                  ("penguins", "nhl", at(2026, 4, 30))):
            self.assertEqual(pts.parse_team_page(fixture(name), league, now)["unparsed"], 0, name)

    def test_page_freshness_is_reported(self):
        block = pts.parse_team_page(fixture("pirates"), "mlb", at(2026, 9, 2))
        self.assertEqual(block["as_of"], "2026-09-02T10:34:35-04:00")   # live page: data-loaded
        block = pts.parse_team_page(fixture("steelers"), "nfl", at(2026, 9, 2))
        self.assertEqual(block["as_of"], "2026-09-02T05:00:00-04:00")   # daily page: publish-time
        # a Monday-morning run on a page still published Sunday names the day
        block = pts.parse_team_page(fixture("steelers"), "nfl", at(2026, 9, 14, 7, 2))
        self.assertEqual(block["games"][0]["result"],
                         "Falcons @ Steelers · started 1:00 PM, result not posted "
                         "as of the Wed Sep 2 5:00 AM page update")

    def test_live_row_is_labelled_in_progress(self):
        page = ('<title>2026 Pittsburgh Pirates</title>\n'
                'G140: We   9/2 v <a class="text-fg" href="/mlb/2026/teams/san-francisco-giants">'
                'Giants</a>       <a class="text-fg live-nav" href="/mlb/2026-09-02/sf-pit">'
                '<span class="text-red">T5</span> 3-2</a>\n')
        block = pts.parse_team_page(page, "mlb", at(2026, 9, 2, 20))
        self.assertEqual(block["games"], [{
            "date": "Wed Sep 2",
            "result": "Giants @ Pirates · T5 3-2 (in progress at last update)",
            "url": f"{SITE}/mlb/2026-09-02/sf-pit", "recap": ""}])

    def test_garbage_unsafe_links_and_entities(self):
        # a page that is not a team page is an error, not the off-season
        for junk in ("<html><body>nope</body></html>", None, b"bytes",
                     "<title>2026 Pittsburgh Pirates</title><p>Season not found</p>"):
            with self.assertRaises(ValueError):
                pts.parse_team_page(junk, "mlb", at(2026, 9, 2))
        page = ('<title>2026 Pittsburgh Pirates</title>\n'
                'G1:   9/1 v <a class="text-fg" href="/mlb/2026/teams/x">Giants &amp; Co</a> '
                '<a class="text-fg game-nav" href="javascript:alert(1)">'
                '<span class="text-green">W</span> 2-1</a>\n')
        block = pts.parse_team_page(page, "mlb", at(2026, 9, 2))
        self.assertEqual(block["games"][0]["result"], "Giants & Co 1 · Pirates 2 · Final")
        self.assertEqual(block["games"][0]["url"], f"{SITE}/mlb/2026/teams/pittsburgh-pirates")

    def test_season_paths_and_urls(self):
        self.assertEqual(pts.season_paths("nhl", at(2026, 9, 2)), ["2026-2027", "2025-2026"])
        self.assertEqual(pts.season_paths("nhl", at(2027, 3, 1)), ["2026-2027", "2027-2028"])
        self.assertEqual(pts.season_paths("nfl", at(2027, 1, 10)), ["2026", "2027"])
        self.assertEqual(pts.season_paths("mlb", at(2026, 6, 1)), ["2026", "2025"])
        self.assertEqual(pts.team_page_url("nhl", "2026-2027"),
                         f"{SITE}/nhl/2026-2027/teams/pittsburgh-penguins")


# --------------------------------------------------------------- fallback

class FrozenDatetime(datetime):
    fixed = at(2026, 9, 2, 10, 35)

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls.fixed.replace(tzinfo=None)
        return cls.fixed.astimezone(tz)


PIRATES_URL = f"{SITE}/mlb/2026/teams/pittsburgh-pirates"
STEELERS_URL = f"{SITE}/nfl/2026/teams/pittsburgh-steelers"
PENGUINS_NEW = f"{SITE}/nhl/2026-2027/teams/pittsburgh-penguins"
PENGUINS_OLD = f"{SITE}/nhl/2025-2026/teams/pittsburgh-penguins"


def fake_site(url, headers=None):
    """plaintextsports as it looked on 2026-09-02: no 2026-2027 NHL page yet."""
    pages = {PIRATES_URL: "pirates", STEELERS_URL: "steelers", PENGUINS_OLD: "penguins"}
    if url in pages:
        return fixture(pages[url])
    raise http_error(url, 404)


class ScoreboardFallback(unittest.TestCase):
    def test_espn_outage_falls_back_per_league(self):
        errors, notes, fetched = [], [], []

        def get_text(url, headers=None):
            fetched.append((url, headers))
            return fake_site(url)

        with mock.patch.object(pittsburgh, "datetime", FrozenDatetime), \
                mock.patch.object(pittsburgh, "_espn_json",
                                  side_effect=RuntimeError("HTTP 403 (server: AkamaiGHost)")), \
                mock.patch.object(pittsburgh, "_get_text", get_text):
            blocks = pittsburgh.sports_blocks(errors=errors, notes=notes)
        self.assertEqual(errors, [])
        # Penguins: the 2026-2027 page 404s, last season's parses as off-season
        self.assertEqual([b["team"] for b in blocks], ["Pirates", "Steelers"])
        self.assertEqual({b["source"] for b in blocks}, {"plaintextsports"})
        self.assertEqual(blocks[0]["games"][0]["result"], "Giants 12 · Pirates 13 · Final")
        self.assertEqual(blocks[1]["next"]["matchup"], "Falcons @ Steelers")
        self.assertEqual([u for u, _ in fetched],
                         [PIRATES_URL, STEELERS_URL, PENGUINS_NEW, PENGUINS_OLD])
        self.assertEqual({h["User-Agent"] for _, h in fetched}, {pittsburgh.USER_AGENT})
        self.assertEqual(len(notes), 3)
        for note in notes:
            self.assertIn("ESPN failed", note)
            self.assertIn("HTTP 403 (server: AkamaiGHost)", note)
            self.assertIn("used plaintextsports", note)

    def test_partial_espn_failure_also_falls_back(self):
        def team_block(sport, league, now_local, now_utc, errors):
            errors.append(f"{league} scoreboard 20260902: HTTP 403")
            return {"team": "Pirates", "record": "68-71", "games": [], "next": None,
                    "source": "ESPN"}
        errors, notes = [], []
        with mock.patch.object(pittsburgh, "datetime", FrozenDatetime), \
                mock.patch.object(pittsburgh, "LEAGUES", [("baseball", "mlb")]), \
                mock.patch.object(pittsburgh, "_team_block", team_block), \
                mock.patch.object(pittsburgh, "_get_text", fake_site):
            blocks = pittsburgh.sports_blocks(errors=errors, notes=notes)
        self.assertEqual(errors, [])
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["source"], "plaintextsports")
        self.assertEqual(len(blocks[0]["games"]), 1)
        self.assertIn("mlb scoreboard 20260902: HTTP 403", notes[0])

    def test_espn_success_never_touches_plaintextsports(self):
        block = {"team": "Pirates", "record": "68-71", "games": [], "next": {
            "matchup": "Giants @ Pirates", "when": "Wed Sep 2, 6:40 PM", "url": ""},
            "source": "ESPN"}
        errors, notes = [], []
        with mock.patch.object(pittsburgh, "LEAGUES", [("baseball", "mlb")]), \
                mock.patch.object(pittsburgh, "_team_block", lambda *a: block), \
                mock.patch.object(pittsburgh, "_get_text",
                                  side_effect=AssertionError("must not fetch")):
            blocks = pittsburgh.sports_blocks(errors=errors, notes=notes)
        self.assertEqual(blocks, [block])
        self.assertEqual((errors, notes), ([], []))

    def test_both_sources_failing_reports_both(self):
        errors, notes = [], []
        with mock.patch.object(pittsburgh, "datetime", FrozenDatetime), \
                mock.patch.object(pittsburgh, "_espn_json", side_effect=RuntimeError("HTTP 403")), \
                mock.patch.object(pittsburgh, "_get_text",
                                  side_effect=http_error(PIRATES_URL, 503, "nginx")):
            blocks = pittsburgh.sports_blocks(errors=errors, notes=notes)
        self.assertEqual(blocks, [])
        self.assertEqual(notes, [])
        self.assertEqual(len(errors), 2 * len(pittsburgh.LEAGUES))
        self.assertEqual(errors[0], "mlb: HTTP 403")
        self.assertEqual(errors[1], "mlb plaintextsports: HTTP 503 (server: nginx)")
        self.assertNotIn("blocked", " ".join(errors))  # the body stays in the log

    def test_partial_espn_data_is_kept_when_the_fallback_fails_too(self):
        def team_block(sport, league, now_local, now_utc, errors):
            errors.append(f"{league} schedule: HTTP 403")
            return {"team": "Pirates", "record": "68-71", "games": [
                {"date": "Tue Sep 1", "result": "Giants 12 · Pirates 13 · Final",
                 "url": "", "recap": ""}], "next": None, "source": "ESPN"}
        errors, notes = [], []
        with mock.patch.object(pittsburgh, "datetime", FrozenDatetime), \
                mock.patch.object(pittsburgh, "LEAGUES", [("baseball", "mlb")]), \
                mock.patch.object(pittsburgh, "_team_block", team_block), \
                mock.patch.object(pittsburgh, "_get_text", side_effect=OSError("timed out")):
            blocks = pittsburgh.sports_blocks(errors=errors, notes=notes)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["source"], "ESPN")
        # an OSError's text comes from the far end, so only its type is published
        self.assertEqual(errors, ["mlb schedule: HTTP 403", "mlb plaintextsports: OSError"])

    def test_only_messages_this_engine_composed_are_published(self):
        import http.client
        self.assertEqual(pittsburgh._reason(RuntimeError("HTTP 403 (server: AkamaiGHost)")),
                         "HTTP 403 (server: AkamaiGHost)")
        self.assertEqual(pittsburgh._reason(ValueError("not a team page (no game rows)")),
                         "not a team page (no game rows)")
        # a remote server picks the text of these, so only the class name ships
        self.assertEqual(pittsburgh._reason(
            http.client.BadStatusLine("Visit https://evil.example NOW")), "BadStatusLine")
        self.assertEqual(pittsburgh._reason(urllib.error.URLError("free prizes here")), "URLError")
        self.assertEqual(pittsburgh._reason(RuntimeError("a\nb" + "x" * 400)),
                         ("a b" + "x" * 400)[:160])

    def test_published_error_text_is_status_and_product_token_only(self):
        headers = email.message.Message()
        headers["Server"] = "Visit https://evil.example NOW for a prize"
        exc = urllib.error.HTTPError(PIRATES_URL, 503, "Service Unavailable", headers,
                                     io.BytesIO(b"<html>drip</html>"))
        self.assertEqual(str(pittsburgh._http_error("plaintextsports x", exc)), "HTTP 503")
        headers.replace_header("Server", "AkamaiGHost")
        exc = urllib.error.HTTPError(PIRATES_URL, 403, "Forbidden", headers, io.BytesIO(b"x"))
        self.assertEqual(str(pittsburgh._http_error("x", exc)), "HTTP 403 (server: AkamaiGHost)")

        class Drip(io.RawIOBase):
            """An error body that would never finish a full read."""
            calls = 0

            def readable(self):
                return True

            def readinto(self, b):
                Drip.calls += 1
                b[0:1] = b"z"
                return 1
        exc = urllib.error.HTTPError(PIRATES_URL, 503, "nope", headers,
                                     io.BufferedReader(Drip()))
        self.assertEqual(str(pittsburgh._http_error("x", exc)), "HTTP 503 (server: AkamaiGHost)")
        self.assertLessEqual(Drip.calls, 2)  # one bounded read, not a drain

    def test_cleaner_caps_urls_and_list_lengths(self):
        long_url = "https://plaintextsports.com/" + "a" * 400
        blocks = [{"team": "Pirates", "record": "1-0", "source": "plaintextsports",
                   "games": [{"date": "d", "result": "r", "url": long_url, "recap": ""}] * 20,
                   "next": {"matchup": "m", "when": "w", "url": "javascript:alert(1)"}}] * 9
        cleaned = generate._clean_sports(blocks)
        self.assertEqual(len(cleaned), 5)
        self.assertEqual(len(cleaned[0]["games"]), 8)
        self.assertEqual(cleaned[0]["games"][0]["url"], "")
        self.assertEqual(cleaned[0]["next"]["url"], "")
        self.assertEqual(cleaned[0]["source"], "plaintextsports")

    def test_unparseable_page_is_an_error_and_partial_espn_data_survives(self):
        def team_block(sport, league, now_local, now_utc, errors):
            errors.append(f"{league} schedule: HTTP 403")
            return {"team": "Pirates", "record": "68-71", "games": [
                {"date": "Tue Sep 1", "result": "Giants 12 · Pirates 13 · Final",
                 "url": "", "recap": ""}], "next": None, "source": "ESPN"}
        errors, notes = [], []
        with mock.patch.object(pittsburgh, "datetime", FrozenDatetime), \
                mock.patch.object(pittsburgh, "LEAGUES", [("baseball", "mlb")]), \
                mock.patch.object(pittsburgh, "_team_block", team_block), \
                mock.patch.object(pittsburgh, "_get_text", lambda url, headers=None:
                                  "<title>Pittsburgh Pirates Schedule</title><p>moved</p>"):
            blocks = pittsburgh.sports_blocks(errors=errors, notes=notes)
        self.assertEqual([b["source"] for b in blocks], ["ESPN"])
        self.assertEqual(errors, ["mlb schedule: HTTP 403",
                                  "mlb plaintextsports: not a team page (no season title)"])
        self.assertEqual(notes, [])

    def test_off_season_fallback_keeps_partial_espn_data(self):
        # ESPN knows next week's game; last season's page shows nothing current
        def team_block(sport, league, now_local, now_utc, errors):
            errors.append(f"{league} scoreboard 20260902: HTTP 403")
            return {"team": "Penguins", "record": "", "games": [], "next": {
                "matchup": "Penguins @ Flyers", "when": "Tue Sep 8, 7:00 PM", "url": ""},
                "source": "ESPN"}
        errors, notes = [], []
        with mock.patch.object(pittsburgh, "datetime", FrozenDatetime), \
                mock.patch.object(pittsburgh, "LEAGUES", [("hockey", "nhl")]), \
                mock.patch.object(pittsburgh, "_team_block", team_block), \
                mock.patch.object(pittsburgh, "_get_text", fake_site):
            blocks = pittsburgh.sports_blocks(errors=errors, notes=notes)
        self.assertEqual([b["source"] for b in blocks], ["ESPN"])
        self.assertEqual(errors, [])
        self.assertEqual(notes, ["nhl: ESPN failed (nhl scoreboard 20260902: HTTP 403); "
                                 "used plaintextsports"])

    def test_stale_page_and_markup_drift_are_noted(self):
        class Later(FrozenDatetime):
            fixed = at(2026, 9, 5, 10, 0)
        errors, notes = [], []
        with mock.patch.object(pittsburgh, "datetime", Later), \
                mock.patch.object(pittsburgh, "LEAGUES", [("football", "nfl")]), \
                mock.patch.object(pittsburgh, "_espn_json", side_effect=RuntimeError("HTTP 403")), \
                mock.patch.object(pittsburgh, "_get_text", fake_site):
            blocks = pittsburgh.sports_blocks(errors=errors, notes=notes)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(errors, [])
        self.assertEqual(notes[1], "nfl: plaintextsports page last published Sep 2")
        drift = {"team": "Steelers", "record": "", "games": [], "next": None,
                 "source": "plaintextsports", "as_of": None, "unparsed": 3}
        self.assertEqual(pittsburgh._pts_health("nfl", drift, at(2026, 9, 5)),
                         ["nfl: 3 plaintextsports rows not understood"])

    def test_season_page_lookup_only_falls_through_on_404(self):
        with mock.patch.object(pittsburgh, "_get_text", fake_site):
            page, url = pittsburgh._pts_page("nhl", at(2026, 9, 2))
        self.assertEqual(url, PENGUINS_OLD)
        self.assertIn("2025-2026 Pittsburgh Penguins", page)
        with mock.patch.object(pittsburgh, "_get_text",
                               side_effect=http_error(PENGUINS_NEW, 403, "cloudflare")):
            with self.assertRaises(RuntimeError) as ctx:
                pittsburgh._pts_page("nhl", at(2026, 9, 2))
        self.assertEqual(str(ctx.exception), "HTTP 403 (server: cloudflare)")
        with mock.patch.object(pittsburgh, "_get_text", side_effect=http_error(PENGUINS_NEW, 404)):
            with self.assertRaises(RuntimeError) as ctx:
                pittsburgh._pts_page("nhl", at(2026, 9, 2))
        self.assertEqual(str(ctx.exception), "HTTP 404 (no season page)")


if __name__ == "__main__":
    unittest.main()
