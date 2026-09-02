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
import unittest
import urllib.error
from datetime import datetime
from unittest import mock

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
                      "as of the 5:00 AM page update",
            "url": f"{SITE}/nfl/2026/week1/atl-pit", "recap": ""}])
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
        self.assertIsNone(pts.parse_team_page("<html><body>nope</body></html>", "mlb", at(2026, 9, 2)))
        self.assertIsNone(pts.parse_team_page(None, "mlb", at(2026, 9, 2)))
        self.assertIsNone(pts.parse_team_page(b"bytes", "mlb", at(2026, 9, 2)))
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
        self.assertEqual(errors, ["mlb schedule: HTTP 403", "mlb plaintextsports: timed out"])

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
