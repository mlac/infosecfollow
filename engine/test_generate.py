"""Tests for the infosecfollow engine (engine/generate.py and friends).

Run from the repository root:

    python3 -m unittest discover -s engine -p 'test_*.py'

No network and no model: feeds are in-memory bytes, the Claude CLI is a stub,
the clock is frozen where the date matters, and the site is written to a
temporary directory. Renderer fixtures live in engine/testdata/ (three
committed day records plus one written by the current engine); the live
docs/data/ records are swept as well when enough of them are present.
"""

import email.message
import gzip
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate  # noqa: E402
import market_data  # noqa: E402
import pittsburgh  # noqa: E402
import plaintextsports  # noqa: E402

NOW = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
TODAY = "2026-09-02"
HERE = Path(__file__).resolve().parent
TESTDATA = HERE / "testdata"
REPO_DOCS = HERE.parent / "docs"


def item(url, title="Title", source="Feed", hours_ago=1.0, summary="s"):
    return {"source": source, "title": title, "url": url,
            "published": NOW - timedelta(hours=hours_ago), "summary": summary}


class OutlineParser(HTMLParser):
    """Collects the heading outline and checks tags balance."""
    VOID = {"meta", "br", "hr", "img", "link", "input"}

    def __init__(self):
        super().__init__()
        self.stack, self.errors, self.headings, self.ids = [], [], [], []

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append(int(tag[1]))
        for k, v in attrs:
            if k == "id":
                self.ids.append(v)
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append(tag)


class FrozenDatetime(datetime):
    """datetime whose now() is pinned to NOW; strptime/fromisoformat still work."""
    fixed = NOW

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls.fixed.astimezone().replace(tzinfo=None)
        return cls.fixed.astimezone(tz)


# --------------------------------------------------------------------- parsing

class FeedParsing(unittest.TestCase):
    ATOM = (b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom" '
            b'xml:base="https://example.org/blog/">'
            b'<entry><title>Post</title><link href="posts/1"/>'
            b'<updated>2026-09-01T10:00:00Z</updated>'
            b'<published>2026-08-01T10:00:00Z</published>'
            b'<summary>Hello</summary></entry>'
            b'<entry><title type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">'
            b'Rich <b>title</b></div></title><link href="https://example.org/2"/>'
            b'<published>2026-09-01T11:00:00Z</published>'
            b'<content type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">'
            b'<p>Body text</p></div></content></entry></feed>')
    RSS = (b'<?xml version="1.0"?><rss version="2.0" '
           b'xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>'
           b'<item><title>Story</title><link>https://example.org/s</link>'
           b'<dc:date>2026-09-01T10:00:00Z</dc:date>'
           b'<pubDate>Sat, 01 Aug 2026 10:00:00 GMT</pubDate>'
           b'<description><![CDATA[<p>Hi &amp; bye</p>]]></description></item>'
           b'<item><title>Podcast</title><guid isPermaLink="false">abc</guid>'
           b'<enclosure url="https://cdn.example.org/ep.mp3" type="audio/mpeg"/>'
           b'<pubDate>Sat, 01 Aug 2026 10:00:00 GMT</pubDate></item>'
           b'<item><title>Bad link</title><link>javascript:alert(1)</link>'
           b'<pubDate>Sat, 01 Aug 2026 10:00:00 GMT</pubDate></item>'
           b'<item><title>Control</title><link>\n  https://example.org/c\xe2\x80\x8b \t</link></item>'
           b'</channel></rss>')

    def test_priority_order_beats_document_order(self):
        items = list(generate.parse_feed("f", self.ATOM))
        self.assertEqual(items[0]["published"].month, 8)  # <published>, not <updated>
        rss = list(generate.parse_feed("f", self.RSS))
        self.assertEqual(rss[0]["published"].month, 8)  # pubDate, not dc:date

    def test_xhtml_title_and_content_are_flattened(self):
        items = list(generate.parse_feed("f", self.ATOM))
        self.assertEqual(items[1]["title"], "Rich title")
        self.assertEqual(items[1]["summary"], "Body text")

    def test_relative_atom_link_resolved_against_xml_base(self):
        items = list(generate.parse_feed("f", self.ATOM, base="https://example.org/feed.xml"))
        self.assertEqual(items[0]["url"], "https://example.org/blog/posts/1")
        # without any base the relative link cannot become an http(s) URL
        bare = list(generate.parse_feed("f", self.ATOM.replace(
            b' xml:base="https://example.org/blog/"', b"")))
        self.assertTrue(all(i["url"].startswith("https://") for i in bare))
        self.assertEqual(len(bare), 1)

    def test_rss_enclosure_fallback_and_bad_urls(self):
        items = list(generate.parse_feed("f", self.RSS))
        urls = {i["title"]: i["url"] for i in items}
        self.assertEqual(urls["Podcast"], "https://cdn.example.org/ep.mp3")
        self.assertNotIn("Bad link", urls)               # javascript: dropped
        self.assertEqual(urls["Control"], "https://example.org/c")  # whitespace, zero-width stripped
        self.assertEqual(urls["Story"], "https://example.org/s")
        self.assertEqual(items[0]["summary"], "Hi & bye")

    def test_transport_charset_used_only_for_undeclared_non_utf8_bodies(self):
        latin = ("<rss version=\"2.0\"><channel><item><title>Caf\xe9</title>"
                 "<link>https://x.example/a</link></item></channel></rss>").encode("latin-1")
        self.assertEqual(list(generate.parse_feed("f", latin, charset="iso-8859-1"))[0]["title"], "Café")
        utf8 = ("<rss version=\"2.0\"><channel><item><title>Pittsburgh’s café</title>"
                "<link>https://x.example/a</link></item></channel></rss>").encode("utf-8")
        self.assertEqual(list(generate.parse_feed("f", utf8, charset="iso-8859-1"))[0]["title"],
                         "Pittsburgh’s café")

    def test_parse_date_edge_cases(self):
        self.assertIsNone(generate.parse_date(""))
        self.assertIsNone(generate.parse_date("not a date"))
        self.assertIsNone(generate.parse_date("9999-12-31T23:59:59-05:00"))  # no OverflowError
        self.assertIsNone(generate.parse_date("0001-01-01T00:00:00+05:00"))
        dt = generate.parse_date("Tue, 01 Sep 2026 10:00:00 -0400")
        self.assertEqual((dt.hour, dt.tzinfo), (14, timezone.utc))

    def test_clean_text_is_linear_on_hostile_input(self):
        for payload in ("<!--" * 250_000, "<" + "a" * 1_000_000, "<a " * 300_000):
            start = time.monotonic()
            generate.clean_text(payload, 480)
            self.assertLess(time.monotonic() - start, 1.0, payload[:8])

    def test_clean_text_strips_tags_comments_and_entities(self):
        self.assertEqual(generate.clean_text("<p>Hi<!-- x --> &lt;b&gt;there&lt;/b&gt;</p>", 100),
                         "Hi there")
        self.assertEqual(generate.clean_text("versions < 2.4 and > 1", 100), "versions < 2.4 and > 1")
        self.assertTrue(generate.clean_text("word " * 200, 50).endswith("..."))

    def test_sanitize_strips_controls_and_invisible_format_characters(self):
        self.assertEqual(generate.sanitize("a\x07b‮c​d﻿e‍f"), "abcde‍f")
        self.assertEqual(generate.sanitize("line\nbreak\ttab"), "line\nbreak\ttab")


class HttpGet(unittest.TestCase):
    def fake_open(self, body, content_type, content_encoding=None):
        headers = email.message.Message()
        headers["Content-Type"] = content_type
        if content_encoding:
            headers["Content-Encoding"] = content_encoding

        class Resp(io.BytesIO):
            pass

        resp = Resp(body)
        resp.headers = headers

        class Ctx:
            def __enter__(self_inner):
                return resp

            def __exit__(self_inner, *a):
                return False

        return lambda req, timeout: Ctx()

    def test_charset_and_gzip(self):
        with mock.patch.object(generate.safefetch, "safe_open",
                               self.fake_open(b"<rss/>", "application/xml; charset=iso-8859-1")):
            self.assertEqual(generate.http_get("https://x.example/f"), (b"<rss/>", "iso-8859-1"))
        packed = gzip.compress(b"<rss>gz</rss>")
        with mock.patch.object(generate.safefetch, "safe_open",
                               self.fake_open(packed, "application/xml", "gzip")):
            self.assertEqual(generate.http_get("https://x.example/f"), (b"<rss>gz</rss>", None))

    def test_post_inflate_size_cap(self):
        bomb = gzip.compress(b"a" * (generate.MAX_FEED_BYTES + 1))
        self.assertLess(len(bomb), generate.MAX_FEED_BYTES)  # compressed size passes read_bounded
        with mock.patch.object(generate.safefetch, "safe_open",
                               self.fake_open(bomb, "application/xml", "gzip")):
            with self.assertRaises(generate.safefetch.ResponseTooLargeError):
                generate.http_get("https://x.example/f")


class Selection(unittest.TestCase):
    def test_recent_items_dedupes_same_headline_same_day_only(self):
        a = item("https://a.example/1", "CISA Adds Two KEVs", hours_ago=2)
        b = item("https://b.example/1", "CISA Adds Two KEVs", hours_ago=3)   # same day, other feed
        c = item("https://a.example/2", "CISA Adds Two KEVs", hours_ago=30)  # previous day
        future = item("https://a.example/3", "Future", hours_ago=-5)
        got = generate.recent_items([a, b, c, future], NOW, 48, 10)
        self.assertEqual([i["url"] for i in got], ["https://a.example/1", "https://a.example/2"])

    def test_select_window_widens_when_thin(self):
        items = [item(f"https://x.example/{n}", f"T{n}", hours_ago=30 + n) for n in range(15)]
        selected, window = generate.select_window(items, NOW)
        self.assertEqual(window, generate.FALLBACK_WINDOW_HOURS)
        self.assertEqual(len(selected), 15)
        many = [item(f"https://x.example/{n}", f"T{n}", hours_ago=1) for n in range(15)]
        self.assertEqual(generate.select_window(many, NOW)[1], generate.WINDOW_HOURS)

    def test_in_window_counts_are_per_feed_before_dedupe(self):
        items = [item("https://a.example/1", "Same headline", source="A", hours_ago=2),
                 item("https://b.example/1", "Same headline", source="B", hours_ago=3),
                 item("https://b.example/2", "Old", source="B", hours_ago=90)]
        self.assertEqual(generate.in_window_counts(items, NOW, 24), {"A": 1, "B": 1})
        self.assertEqual(len(generate.recent_items(items, NOW, 24, 10)), 1)  # dedupe kept one

    def test_order_topics_newest_day_then_popularity_then_original_order(self):
        pub = {"https://a.example/1": NOW - timedelta(days=2),
               "https://b.example/1": NOW - timedelta(hours=1),
               "https://c.example/1": NOW - timedelta(hours=2),
               "https://c.example/2": NOW - timedelta(hours=3)}
        digest = {"topics": [
            {"title": "old", "sources": [{"url": "https://a.example/1"}]},
            {"title": "today-one-source", "sources": [{"url": "https://b.example/1"}]},
            {"title": "today-two-sources", "sources": [{"url": "https://c.example/1"},
                                                       {"url": "https://c.example/2"}]},
            {"title": "today-one-source-later", "sources": [{"url": "https://b.example/1"}]},
        ]}
        generate.order_topics(digest, generate.published_index([]) | pub)
        self.assertEqual([t["title"] for t in digest["topics"]],
                         ["today-two-sources", "today-one-source", "today-one-source-later", "old"])


# ------------------------------------------------------------------ validation

def digest_reply(sources):
    return {"headline": "Head", "emerging_trends": [{"text": "trend", "topic_title": "T"}],
            "topics": [{"title": "T", "area": "A", "latest_developments": "new",
                        "summary": "sum", "tags": ["x", "", 3, "Y"], "sources": sources}]}


class DigestValidation(unittest.TestCase):
    ALLOWED = {"https://ok.example/1": "Feed One", "https://ok.example/2": "Feed Two"}

    def test_sources_canonical_and_deduped(self):
        reply = digest_reply([{"source": "Reworded", "url": "https://ok.example/1", "title": "t"},
                              {"source": "x", "url": "https://ok.example/1"},
                              {"source": "x", "url": "https://bad.example/1"},
                              {"source": "x", "url": "https://ok.example/2"}])
        out = generate.validate_digest(reply, self.ALLOWED)
        self.assertEqual([s["source"] for s in out["topics"][0]["sources"]], ["Feed One", "Feed Two"])
        self.assertEqual(out["topics"][0]["tags"], ["x", "y"])

    def test_sources_capped(self):
        allowed = {f"https://ok.example/{n}": f"Feed {n}" for n in range(generate.MAX_SOURCES + 2)}
        reply = digest_reply([{"url": u} for u in allowed])
        out = generate.validate_digest(reply, allowed)
        self.assertEqual(len(out["topics"][0]["sources"]), generate.MAX_SOURCES)

    def test_strict_rejects_dropped_topic_lenient_keeps_rest(self):
        reply = digest_reply([{"url": "https://bad.example/1"}])
        reply["topics"].append({"title": "Good", "area": "A", "latest_developments": "n",
                                "summary": "s", "sources": [{"url": "https://ok.example/2"}]})
        with self.assertRaises(ValueError):
            generate.validate_digest(json.loads(json.dumps(reply)), self.ALLOWED, strict=True)
        out = generate.validate_digest(reply, self.ALLOWED, strict=False)
        self.assertEqual([t["title"] for t in out["topics"]], ["Good"])

    def test_nothing_valid_fails_even_lenient(self):
        with self.assertRaises(ValueError):
            generate.validate_digest(digest_reply([{"url": "https://bad.example/1"}]),
                                     self.ALLOWED, strict=False)
        with self.assertRaises(ValueError):
            generate.validate_digest({"headline": "", "emerging_trends": [], "topics": []},
                                     self.ALLOWED, strict=False)

    def test_topics_capped_and_strings_sanitized(self):
        reply = digest_reply([{"url": "https://ok.example/1"}])
        reply["topics"] = [dict(reply["topics"][0], title=f"T\x07{n}") for n in range(15)]
        out = generate.validate_digest(reply, self.ALLOWED)
        self.assertEqual(len(out["topics"]), generate.MAX_TOPICS)
        self.assertEqual(out["topics"][0]["title"], "T0")


def local_item(url, title="Item", latest="new", summary="sum"):
    return {"title": title, "latest_developments": latest, "summary": summary,
            "sources": [{"url": url}]}


class LocalValidation(unittest.TestCase):
    def setUp(self):
        pgh = {f"https://pgh.example/{n}": "TribLive" for n in range(20)}
        self.allowed = {"business_politics": {"https://wsj.example/1": "WSJ"},
                        "business": pgh, "around_town": pgh, "events": pgh,
                        "around_teams": {"https://pg.example/1": "PG Steelers",
                                         "https://pg.example/2": "PG Penguins"},
                        "team_usa": {"https://espn.example/1": "ESPN Olympics"},
                        "reading": {"https://z.example/1": "Ed Zitron",
                                    "https://z.example/2": "Ed Zitron",
                                    "https://s.example/1": "Stratechery"}}
        self.authors = ["Ed Zitron", "Stratechery", "Cal Newport"]

    def validate(self, reply, strict=True, have_reading=True):
        return generate.validate_local(reply, self.allowed, True, have_reading, self.authors, strict)

    def test_caps_cover_a_full_day_of_carried_items(self):
        cap = generate.SECTION_CAPS["business"]
        self.assertGreaterEqual(cap, 4 * 3)  # four weekday runs of up to three new items
        reply = {"business": [local_item(f"https://pgh.example/{n}", f"B{n}") for n in range(cap + 2)],
                 "reading": []}
        out = self.validate(reply, have_reading=False)
        self.assertEqual([i["title"] for i in out["business"]], [f"B{n}" for n in range(cap)])
        self.assertEqual(out["business"][0]["sources"][0]["source"], "TribLive")
        self.assertEqual(out["events"], [])  # omitted key becomes an empty list

    def test_violence_backstop_matches_incidents_not_statistics_or_sports(self):
        reply = {
            "around_town": [local_item("https://pgh.example/1", "Shooting on Penn Avenue",
                                       "Police said the man was fatally shot"),
                            local_item("https://pgh.example/2", "Budget", "Council passed it",
                                       "Homicides fell 12 percent and the police budget grew"),
                            local_item("https://pgh.example/3", "Court", "A jury convicted him",
                                       "He was charged with murder in the Oakland case")],
            "around_teams": [local_item("https://pg.example/1", "Penguins Shooting More",
                                        "Crosby is shooting more from the slot; shooting percentage up")],
            "team_usa": [local_item("https://espn.example/1", "USA Shooting Names Roster",
                                    "USA Shooting announced its Olympic trials roster")],
            "reading": [],
        }
        out = self.validate(reply, have_reading=False)
        self.assertEqual([i["title"] for i in out["around_town"]], ["Budget"])
        self.assertEqual(len(out["around_teams"]), 1)
        self.assertEqual(len(out["team_usa"]), 1)

    def test_reading_author_enum_and_one_per_author(self):
        reply = {"business": [local_item("https://pgh.example/1")],
                 "reading": [{"author": "ed zitron", "title": "A", "url": "https://z.example/1", "summary": "s"},
                             {"author": "Ed Zitron", "title": "B", "url": "https://z.example/2", "summary": "s"},
                             {"author": "Nobody", "title": "C", "url": "https://s.example/1", "summary": "s"}]}
        out = self.validate(reply)
        self.assertEqual([(r["author"], r["title"]) for r in out["reading"]], [("Ed Zitron", "A")])

    def test_empty_pittsburgh_is_error_only_when_strict(self):
        reply = {"business": [local_item("https://bad.example/1")],
                 "reading": [{"author": "Stratechery", "title": "t", "url": "https://s.example/1",
                              "summary": "s"}]}
        with self.assertRaises(ValueError):
            self.validate(json.loads(json.dumps(reply)), strict=True)
        out = self.validate(reply, strict=False)
        self.assertEqual(out["business"], [])
        self.assertEqual(len(out["reading"]), 1)


class Citable(unittest.TestCase):
    def test_carried_sources_are_citable_with_feed_names(self):
        items = [item("https://a.example/1", source="Feed A")]
        carried = [{"title": "T", "sources": [{"source": "Feed B", "url": "https://b.example/9"}]},
                   {"author": "Ed Zitron", "url": "https://z.example/1"}]
        allowed = generate.citable(items, carried)
        self.assertEqual(allowed, {"https://a.example/1": "Feed A",
                                   "https://b.example/9": "Feed B",
                                   "https://z.example/1": "Ed Zitron"})


# ------------------------------------------------------------------- CLI call

class CliInvocation(unittest.TestCase):
    def setUp(self):
        generate._CLI_HELP.clear()
        generate._RUN_DEADLINE = None

    def tearDown(self):
        generate._CLI_HELP.clear()
        generate._RUN_DEADLINE = None

    def test_argv_uses_allowlist_fallback_and_no_persistence_when_supported(self):
        generate._CLI_HELP["/bin/claude"] = "--tools --fallback-model --no-session-persistence"
        argv = generate.claude_argv("/bin/claude")
        self.assertEqual(argv[:4], ["/bin/claude", "-p", "--model", generate.MODEL])
        self.assertIn("--fallback-model", argv)
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        self.assertIn("--no-session-persistence", argv)
        self.assertEqual(argv[-3:], ["--strict-mcp-config", "--setting-sources", ""])
        self.assertIn("--output-format", argv)
        self.assertEqual(argv[argv.index("--output-format") + 1], "json")

    def test_argv_degrades_on_old_cli(self):
        generate._CLI_HELP["/bin/old"] = "--disallowedTools only"
        argv = generate.claude_argv("/bin/old")
        for flag in ("--tools", "--fallback-model", "--no-session-persistence"):
            self.assertNotIn(flag, argv)
        self.assertIn("--disallowedTools", argv)

    def test_env_strips_git_credentials_only(self):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "x", "GIT_REMOTE_URL": "y",
                                          "GH_TOKEN": "z", "CLAUDE_CODE_OAUTH_TOKEN": "keep",
                                          "HTTPS_PROXY": "keep", "TZ": "keep"}):
            env = generate._cli_env()
        for k in ("GITHUB_TOKEN", "GIT_REMOTE_URL", "GH_TOKEN"):
            self.assertNotIn(k, env)
        for k in ("CLAUDE_CODE_OAUTH_TOKEN", "HTTPS_PROXY", "TZ", "PATH"):
            self.assertIn(k, env)

    def test_parse_cli_output_shapes(self):
        obj = {"type": "result", "result": "{\"a\":1}", "is_error": False, "duration_ms": 1200,
               "total_cost_usd": 0.5, "modelUsage": {"claude-opus-9": {"inputTokens": 10,
                                                                        "outputTokens": 2, "x": "no"}}}
        text, info = generate._parse_cli_output(json.dumps(obj))
        self.assertEqual(text, '{"a":1}')
        self.assertEqual(info["models"], ["claude-opus-9"])
        self.assertEqual(info["usage"]["claude-opus-9"], {"inputTokens": 10, "outputTokens": 2})
        self.assertEqual((info["cost_usd"], info["duration_ms"]), (0.5, 1200))
        text, info = generate._parse_cli_output(json.dumps([{"type": "system"}, obj]))
        self.assertEqual(text, '{"a":1}')
        text, info = generate._parse_cli_output("plain {\"a\":1}")
        self.assertEqual((text, info["models"]), ("plain {\"a\":1}", []))
        with self.assertRaises(RuntimeError):
            generate._parse_cli_output(json.dumps({"result": "boom", "is_error": True}))

    def test_run_claude_uses_stripped_env_and_scratch_cwd(self):
        generate._CLI_HELP["/bin/claude"] = ""
        seen = {}

        def fake_run(argv, **kw):
            seen.update(kw)
            return subprocess.CompletedProcess(argv, 0, stdout='{"result":"{}"}', stderr="")

        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "secret"}), \
                mock.patch.object(generate.subprocess, "run", fake_run):
            text, info = generate.run_claude("/bin/claude", "prompt")
        self.assertEqual(text, "{}")
        self.assertNotIn("GITHUB_TOKEN", seen["env"])
        self.assertEqual(seen["input"], "prompt")
        self.assertEqual(seen["timeout"], generate.CLI_TIMEOUT)
        self.assertFalse(os.path.exists(seen["cwd"]))  # scratch dir removed

    def test_run_claude_surfaces_the_envelope_error_text(self):
        generate._CLI_HELP["/bin/claude"] = ""
        envelope = json.dumps({"type": "result", "subtype": "error_during_execution",
                               "is_error": True, "duration_ms": 5, "session_id": "x" * 300,
                               "errors": ["Invalid API key · Please run /login"]})

        def fake_run(argv, **kw):
            return subprocess.CompletedProcess(argv, 1, stdout=envelope, stderr="")

        with mock.patch.object(generate.subprocess, "run", fake_run):
            with self.assertRaises(RuntimeError) as ctx:
                generate.run_claude("/bin/claude", "prompt")
        self.assertIn("Invalid API key", str(ctx.exception))
        self.assertNotIn("xxxxxxxx", str(ctx.exception))

    def test_run_budget_caps_timeouts_and_refuses_hopeless_calls(self):
        generate._CLI_HELP["/bin/claude"] = ""
        seen = {}

        def fake_run(argv, **kw):
            seen.update(kw)
            return subprocess.CompletedProcess(argv, 0, stdout='{"result":"{}"}', stderr="")

        with mock.patch.object(generate.subprocess, "run", fake_run):
            generate.start_run_clock(budget=400)
            generate.run_claude("/bin/claude", "p")
            self.assertLessEqual(seen["timeout"], 390)
            self.assertLess(seen["timeout"], generate.CLI_TIMEOUT)
            generate.start_run_clock(budget=60)
            with self.assertRaises(RuntimeError):
                generate.run_claude("/bin/claude", "p")
        self.assertGreater(generate.run_seconds_left(), 0)

    def test_ask_claude_retries_process_failures_with_backoff(self):
        calls = {"n": 0}

        def flaky(cli, prompt, timeout=None):
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("claude CLI exited 1: overloaded")
            return '{"ok": true}', {"models": ["m"], "usage": {}, "cost_usd": 0, "duration_ms": 1}

        sleeps = []
        with mock.patch.object(generate, "run_claude", flaky), \
                mock.patch.object(generate.time, "sleep", sleeps.append):
            out, info = generate.ask_claude("/bin/claude", "p", lambda d, strict: d)
        self.assertEqual(out, {"ok": True})
        self.assertEqual(sleeps, [generate.CLI_BACKOFF[0], generate.CLI_BACKOFF[1]])

    def test_ask_claude_gives_up_after_attempts_or_budget(self):
        with mock.patch.object(generate, "run_claude",
                               mock.Mock(side_effect=RuntimeError("down"))) as run, \
                mock.patch.object(generate.time, "sleep", lambda s: None):
            with self.assertRaises(RuntimeError):
                generate.ask_claude("/bin/claude", "p", lambda d, strict: d)
            self.assertEqual(run.call_count, generate.CLI_ATTEMPTS)
            run.reset_mock()
            generate.start_run_clock(budget=generate.MIN_CALL_SECONDS + 20)  # room for one call only
            with self.assertRaises(RuntimeError):
                generate.ask_claude("/bin/claude", "p", lambda d, strict: d)
            self.assertEqual(run.call_count, 1)
            run.reset_mock()
            generate._RUN_DEADLINE = None
            with self.assertRaises(RuntimeError):
                generate.ask_claude("/bin/claude", "p", lambda d, strict: d, attempts=1)
            self.assertEqual(run.call_count, 1)

    def test_ask_claude_repairs_once_then_relaxes(self):
        prompts, strict_flags = [], []

        def run(cli, prompt, timeout=None):
            prompts.append(prompt)
            return "not json" if len(prompts) == 1 else '{"partial": 1}', {}

        def validate(data, strict):
            strict_flags.append(strict)
            return data

        with mock.patch.object(generate, "run_claude", run):
            out, _ = generate.ask_claude("/bin/claude", "p", validate)
        self.assertEqual(out, {"partial": 1})
        self.assertIn("previous reply was rejected", prompts[1])
        self.assertEqual(strict_flags, [False])  # second reply validated leniently

    def test_timeout_is_a_process_failure_not_a_repair(self):
        outputs = iter([subprocess.TimeoutExpired("claude", 1), ('{"a":1}', {})])

        def run(cli, prompt, timeout=None):
            nxt = next(outputs)
            if isinstance(nxt, Exception):
                raise nxt
            self.assertNotIn("rejected", prompt)
            return nxt

        with mock.patch.object(generate, "run_claude", run), \
                mock.patch.object(generate.time, "sleep", lambda s: None):
            out, _ = generate.ask_claude("/bin/claude", "p", lambda d, strict: d)
        self.assertEqual(out, {"a": 1})

    def test_find_claude_cli_rejects_bad_override(self):
        with mock.patch.dict(os.environ, {"INFOSECFOLLOW_CLAUDE_BIN": "/nonexistent/claude"}):
            with self.assertRaises(RuntimeError):
                generate.find_claude_cli()


# ------------------------------------------------------------ diff and glance

class ChangeDetection(unittest.TestCase):
    def test_reordered_sources_are_the_same_story(self):
        prev = {"topics": [{"title": "T", "latest_developments": "same text",
                            "sources": [{"url": "https://a.example/1"}, {"url": "https://b.example/2"}]}]}
        digest = {"topics": [{"title": "T", "latest_developments": "same text", "_anchor": "i-1",
                              "sources": [{"url": "https://B.example/2"}, {"url": "https://c.example/3"}]}]}
        self.assertEqual(generate.build_candidates(prev, digest, None), [])
        digest["topics"][0]["latest_developments"] = "new text"
        cands = generate.build_candidates(prev, digest, None)
        self.assertEqual([(c["status"], c["old_text"]) for c in cands], [("updated", "same text")])
        digest["topics"][0]["sources"] = [{"url": "https://d.example/4"}]
        self.assertEqual(generate.build_candidates(prev, digest, None)[0]["status"], "new")

    def test_glance_status_reflects_any_linked_story(self):
        catalog = {"i-1": {"status": "unchanged", "title": "One"},
                   "i-2": {"status": "new", "title": "Two"}}
        entries = [{"kind": "Update", "text": "Alpha and Beta moved",
                    "links": [{"anchor": "i-1", "phrase": "Alpha"}, {"anchor": "i-2", "phrase": "Beta"}]},
                   {"kind": "Update", "text": "Nothing linked", "links": []},
                   {"kind": "Trend", "text": "Gamma rises", "links": [{"anchor": "i-1", "phrase": "Gamma"}]}]
        out = generate._normalize_glance(entries, catalog, {"i-1", "i-2"})
        self.assertEqual([(e["kind"], e["status"]) for e in out], [("Update", "new"), ("Trend", None)])
        self.assertEqual([l["anchor"] for l in out[1]["links"]], [])  # i-1 already used

    def test_build_glance_falls_back_to_legacy_synthesis(self):
        digest = {"topics": [{"title": "Topic One", "latest_developments": "d", "summary": "s",
                              "sources": [{"url": "https://a.example/1"}]}],
                  "emerging_trends": [{"text": "Topic One matters", "topic_title": "Topic One",
                                       "link_phrase": "Topic One"}]}
        with mock.patch.object(generate, "ask_claude", side_effect=RuntimeError("no model")):
            glance, info = generate.build_glance("/bin/claude", None, digest, None)
        self.assertIsNone(info)
        self.assertEqual([e["kind"] for e in glance], ["Trend"])
        self.assertEqual(glance[0]["links"][0]["anchor"], digest["topics"][0]["_anchor"])


# -------------------------------------------------------------------- archive

class TempSite(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="infosecfollow-test-"))
        (self.tmp / "data").mkdir()
        (self.tmp / "archive").mkdir()
        self.patcher = mock.patch.object(generate, "SITE_DIR", self.tmp)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_record(self, date, **extra):
        rec = {"date": date, "headline": "h", "emerging_trends": [], "topics": [
            {"title": f"Topic {date}", "area": "A", "latest_developments": "d", "summary": "s",
             "sources": [{"source": "Feed", "url": f"https://x.example/{date}"}]}],
            "local": {"business": [local_item(f"https://pgh.example/{date}", "Biz")]},
            "meta": {"generated_at": f"{date} 07:05 EDT"}}
        rec.update(extra)
        (self.tmp / "data" / f"{date}.json").write_text(json.dumps(rec), encoding="utf-8")
        return rec


class ArchiveMemory(TempSite):
    def test_today_is_carried_not_aged(self):
        self.write_record("2026-09-01")
        self.write_record(TODAY)
        prior = generate.recent_archive_digests(TODAY)
        self.assertEqual([d["date"] for d in prior], ["2026-09-01"])
        prior_local = generate.recent_archive_local(TODAY)
        self.assertEqual([d["date"] for d in prior_local], ["2026-09-01"])
        carried = generate.today_so_far(TODAY)
        self.assertEqual(carried["topics"][0]["title"], f"Topic {TODAY}")
        self.assertEqual(carried["generated_at"], f"{TODAY} 07:05 EDT")
        self.assertIn("TODAY_SO_FAR —", generate.build_prompt([], 24, TODAY, prior, carried))
        self.assertNotIn("TODAY_SO_FAR —", generate.build_prompt([], 24, TODAY, prior, None))
        self.assertIsNone(generate.today_so_far("2026-09-03"))

    def test_legacy_flat_local_shape_is_still_read(self):
        self.write_record("2026-09-01", local={"around_town": [
            {"title": "Old Item", "text": "legacy text field"}]})
        prior_local = generate.recent_archive_local(TODAY)
        self.assertEqual(prior_local[0]["around_town"], ["Old Item — legacy text field"])

    def test_lookback_is_independent_of_retention(self):
        self.write_record("2026-08-28")  # five days old
        with mock.patch.object(generate, "ARCHIVE_RETENTION_DAYS", 1):
            dated = generate._archive_dates_within(TODAY, generate.PRIOR_LOOKBACK_DAYS)
            self.assertEqual([d for _, d in dated], ["2026-08-28"])
            self.assertEqual([d["date"] for d in generate.recent_archive_digests(TODAY)],
                             ["2026-08-28"])

    def test_prune_off_when_zero_and_bounded_when_on(self):
        for d in ("2026-05-01", "2026-09-01"):
            self.write_record(d)
            (self.tmp / "archive" / f"{d}-0705.html").write_text("x")
        generate.prune_old_archives(TODAY, 0)
        self.assertTrue((self.tmp / "data" / "2026-05-01.json").exists())
        generate.prune_old_archives(TODAY, 30)
        self.assertFalse((self.tmp / "data" / "2026-05-01.json").exists())
        self.assertFalse((self.tmp / "archive" / "2026-05-01-0705.html").exists())
        self.assertTrue((self.tmp / "data" / "2026-09-01.json").exists())

    def test_local_fallback_prefers_today_then_yesterday_only(self):
        carried = {"date": TODAY, "generated_at": "today 07:05", "local": {"business": [local_item("u")]}}
        prev = {"date": "2026-09-01", "meta": {"generated_at": "yday 19:35"},
                "local": {"reading": [{"author": "A", "title": "t", "url": "u", "summary": "s"}]}}
        self.assertEqual(generate.choose_local_fallback(carried, prev, TODAY)[1], "today 07:05")
        self.assertEqual(generate.choose_local_fallback(None, prev, TODAY)[1], "yday 19:35")
        stale = dict(prev, date="2026-08-30")
        self.assertEqual(generate.choose_local_fallback(None, stale, TODAY), (None, None))
        empty = {"date": TODAY, "local": {"business": []}}
        self.assertEqual(generate.choose_local_fallback(empty, None, TODAY), (None, None))


class SiteWriting(TempSite):
    def test_atomic_write_never_leaves_a_truncated_target(self):
        target = self.tmp / "index.html"
        target.write_text("old", encoding="utf-8")
        with mock.patch.object(generate.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                generate._atomic_write(target, "new")
        self.assertEqual(target.read_text(encoding="utf-8"), "old")
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()),
                         ["archive", "data", "index.html", "index.html.tmp"])

    def test_write_site_writes_every_file_atomically_and_records_everything(self):
        digest = {"date": TODAY, "headline": "Head", "emerging_trends": [],
                  "topics": [{"title": "T", "area": "A", "latest_developments": "d",
                              "summary": "s", "tags": [], "sources": [{"source": "F", "url": "https://x.example/1"}]}]}
        health = {"groups": [], "aux": [{"label": "Scores (ESPN)", "ok": False, "detail": "no scoreboard"}],
                  "cli": {"models": ["m"], "calls": 1, "cost_usd": 0.1, "duration_ms": 1000}}
        feeds = generate.load_feeds()
        with mock.patch.object(generate.os, "replace", wraps=os.replace) as replace:
            generate.write_site(digest, None, [], [], [], feeds, 5, 24, glance=[],
                                notes=["Quiet day"], health=health, meta_extra={"served_by": ["m"]})
        replaced = sorted(Path(c.args[1]).relative_to(self.tmp).as_posix() for c in replace.call_args_list)
        # archive pages are stamped from the wall clock, so match their shape
        # rather than TODAY (the runner's local date may differ)
        stamped = re.compile(r"archive/\d{4}-\d{2}-\d{2}-\d{4}\.(html|txt)$")
        self.assertEqual([r for r in replaced if not stamped.match(r)],
                         [f"archive/index.html", f"data/{TODAY}.json", "digest.txt", "index.html"])
        self.assertEqual(len([r for r in replaced if stamped.match(r)]), 2)
        self.assertEqual(list(self.tmp.rglob("*.tmp")), [])
        rec = json.loads((self.tmp / "data" / f"{TODAY}.json").read_text())
        self.assertEqual(rec["feed_health"]["aux"][0]["label"], "Scores (ESPN)")
        self.assertEqual(rec["meta"]["served_by"], ["m"])
        self.assertEqual(rec["notes"], ["Quiet day"])
        self.assertIn("glance", rec)
        html = (self.tmp / "index.html").read_text()
        self.assertIn("Feed Health", html)
        self.assertIn("Quiet day", html)
        self.assertIn("<main", html)
        self.assertIn('rel="canonical"', html)
        archive_page = next(p for p in (self.tmp / "archive").glob("*.html") if p.stem != "index")
        self.assertNotIn('rel="canonical"', archive_page.read_text())
        self.assertIn("FEED HEALTH", (self.tmp / "digest.txt").read_text())


class FeedHealth(unittest.TestCase):
    def test_silent_feed_detection_uses_raw_window_counts(self):
        feeds = {g: [] for g in generate.FEED_GROUPS}
        feeds["security"] = [{"name": "A", "url": "u"}, {"name": "B", "url": "u"},
                             {"name": "Dead", "url": "u"}, {"name": "Down", "url": "u"}]
        stats = {"A": {"items": 5, "dated": 5, "error": None}, "B": {"items": 5, "dated": 5, "error": None},
                 "Dead": {"items": 3, "dated": 3, "error": None},
                 "Down": {"items": 0, "dated": 0, "error": "OSError: refused\x07"}}
        selected = {"security": [item("https://a.example/1", "Shared", source="A")]}  # B deduped away
        raw = {"security": {"A": 1, "B": 1}}
        health = generate.build_feed_health(feeds, stats, selected, {"security": 24},
                                            [], {}, per_feed_window=raw)
        sec = health["groups"][0]
        self.assertEqual(sec["empty"], ["Dead"])
        self.assertEqual(sec["per_feed"]["B"], {"items": 5, "in_window": 1, "contributed": 0})
        self.assertEqual(sec["failed"], [{"name": "Down", "error": "OSError: refused"}])
        lines = generate._health_lines(health)
        self.assertIn("No recent items: Dead.", lines[0])
        self.assertNotIn("B", lines[0].split("No recent items")[1])


# ------------------------------------------------------------------- rendering

class Rendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.feeds = generate.load_feeds()
        cls.records = [json.loads(p.read_text(encoding="utf-8"))
                       for p in sorted(TESTDATA.glob("*.json"))]
        live = [json.loads(p.read_text(encoding="utf-8"))
                for p in sorted((REPO_DOCS / "data").glob("*.json"))[-20:]]
        cls.live = [r for r in live if r.get("topics") and "latest_developments" in r["topics"][0]
                    and all(k in r for k in ("date", "headline", "emerging_trends"))]

    def render(self, rec, depth=0):
        digest = {k: rec[k] for k in ("date", "headline", "emerging_trends", "topics")}
        local = rec.get("local")
        generate.assign_anchors(digest, local)
        sports = generate._clean_sports(rec.get("sports") or [])
        html = generate.render_html(digest, local, rec.get("markets") or [], rec.get("weather") or [],
                                    sports, self.feeds, "2026-09-01 19:35 EDT", "7:35 PM EDT",
                                    "archive/index.html", "digest.txt", depth=depth,
                                    glance=rec.get("glance") or [], notes=rec.get("notes"),
                                    health=rec.get("feed_health"))
        text = generate.render_text(digest, local, rec.get("markets") or [], rec.get("weather") or [],
                                    sports, self.feeds, "2026-09-01 19:35 EDT", "7:35 PM EDT",
                                    glance=rec.get("glance") or [], notes=rec.get("notes"),
                                    health=rec.get("feed_health"))
        return html, text

    def check_record(self, rec):
        html, text = self.render(rec)
        p = OutlineParser()
        p.feed(html)
        self.assertEqual((p.stack, p.errors), ([], []), rec["date"])
        for a, b in zip(p.headings, p.headings[1:]):
            self.assertLessEqual(b, a + 1, f"{rec['date']}: heading jumps {a} -> {b}")
        self.assertEqual(len(p.ids), len(set(p.ids)), f"{rec['date']}: duplicate ids")
        targets = set(p.ids)
        for m in re.finditer(r'href="#([^"]+)"', html):
            self.assertIn(m.group(1), targets, rec["date"])
        self.assertIn('class="skip"', html)
        self.assertIn("Jump to:", html)
        self.assertIn("CONTENTS:", text)
        for topic in rec["topics"]:
            self.assertIn(topic["title"].upper()[:20], text)
        return html, text

    def test_fixture_records_render_valid_html_with_sound_outline(self):
        self.assertGreaterEqual(len(self.records), 4)
        for rec in self.records:
            self.check_record(rec)

    def test_new_engine_fixture_renders_every_new_section(self):
        rec = json.loads((TESTDATA / "new-engine-2026-09-01.json").read_text(encoding="utf-8"))
        html, text = self.check_record(rec)
        for needle in ("Feed Health", "Quiet day", "carried over", "Scoreboard unavailable",
                       "AkamaiGHost", "Google Project Zero", 'class="glance trend"'):
            self.assertIn(needle, html, needle)
        for needle in ("FEED HEALTH", "Quiet day", "carried over", "EMERGING TRENDS"):
            self.assertIn(needle, text, needle)

    def test_live_records_render(self):
        if len(self.live) < 6:
            self.skipTest("fewer than six live day records in docs/data")
        for rec in self.live:
            self.check_record(rec)

    def test_reading_markets_and_health_are_folded_shut_and_nothing_else_is(self):
        rec = json.loads((TESTDATA / "new-engine-2026-09-01.json").read_text(encoding="utf-8"))
        html, text = self.check_record(rec)
        folds = re.findall(r'<details class="fold"([^>]*)>\n<summary><h2>([^<]+)</h2></summary>', html)
        self.assertEqual([(attrs.strip(), title) for attrs, title in folds],
                         [('id="reading"', "Reading"), ('id="markets"', "Markets"),
                          ('id="health"', "Feed Health")])
        self.assertNotIn("open", "".join(a for a, _ in folds))  # collapsed by default
        # the sections that carry the day's news keep their plain headings
        self.assertEqual(re.findall(r'<h2 id="([^"]+)">', html),
                         ["glance", "security", "business", "pittsburgh", "sports"])
        for anchor in generate.COLLAPSED_SECTIONS:
            self.assertNotIn(f'<h2 id="{anchor}"', html)
        # the jump index still offers all eight, and the text digest is untouched
        jump = re.search(r'<nav class="jump".*?</nav>', html, re.S).group(0)
        for label in ("Reading", "Markets", "Feed Health"):
            self.assertIn(f">{label}</a>", jump)
        self.assertNotIn("<details", text)
        for heading in ("READING", "MARKETS", "FEED HEALTH"):
            self.assertIn(heading, text)

    def test_around_the_teams_and_team_usa_fold_inside_the_sports_section(self):
        rec = json.loads((TESTDATA / "new-engine-2026-09-01.json").read_text(encoding="utf-8"))
        html, text = self.check_record(rec)
        subs = re.findall(r'<details class="fold sub"><summary><h3>([^<]+)</h3></summary>', html)
        self.assertEqual(subs, ["Around the Teams", "Team USA"])
        for title in ("Around the Teams", "Team USA"):  # the only <h3> is the folded one
            self.assertEqual(html.count(f"<h3>{title}</h3>"),
                             html.count(f"<summary><h3>{title}</h3></summary>"), title)
        self.assertNotIn('class="fold sub" open', html)      # collapsed by default
        # they stay inside Sports, whose own heading is not folded
        sports = html.split('<h2 id="sports">')[1].split("<details class=\"fold\" id=")[0]
        self.assertIn('<details class="fold sub">', sports)
        # the scoreboard above them is still shown outright (this fixture's
        # ESPN call failed, so it is the outage note rather than team lines)
        self.assertIn(generate.SCOREBOARD_NOTE, sports)
        self.assertLess(sports.index(generate.SCOREBOARD_NOTE),
                        sports.index('<details class="fold sub">'))
        for heading in ("Around the Teams:", "Team USA:"):  # the digest keeps them inline
            self.assertIn(heading, text)

    def test_a_jump_link_into_a_folded_section_is_opened_by_the_page_script(self):
        rec = json.loads((TESTDATA / "new-engine-2026-09-01.json").read_text(encoding="utf-8"))
        html, _ = self.render(rec)
        # the glance list links to individual reading items, which now sit
        # inside a closed <details>; without the opener those jumps go nowhere
        reading_block = html.split('<details class="fold" id="reading">')[1].split("</details>")[0]
        item_ids = set(re.findall(r'<li id="([^"]+)"', reading_block))
        self.assertTrue(item_ids)
        script = html.split("<script>")[1].split("</script>")[0]
        for needle in ("location.hash", 'p.tagName === "DETAILS"', "p.open = true",
                       "hashchange", "scrollIntoView"):
            self.assertIn(needle, script)
        self.assertEqual(html.count("<script>"), 1)
        self.assertNotIn("<script", html.split("</footer>")[0])  # after the content, once

    def test_carry_forward_caps_reach_the_model_as_numbers(self):
        carried = {"local": {"business": [
            {"title": "Budget Passes", "latest_developments": "d", "summary": "s",
             "sources": [{"source": "F", "url": "https://x.example/1"}]}]}}
        prompt = generate.build_local_prompt([], [], [], [], [], [], TODAY, None,
                                             carried, self.feeds)
        self.assertIn("Carry forward EVERY item", prompt)
        self.assertIn(f"at most {generate.SECTION_CAPS['business']} items in total "
                      f"(business_politics {generate.SECTION_CAPS['business_politics']})", prompt)
        self.assertNotIn("SECTION_CAPS[", prompt)  # the caps were once shipped as literals

    def test_source_label_fallback_matches_between_renditions(self):
        digest = {"date": TODAY, "headline": "H", "emerging_trends": [], "topics": [
            {"title": "T", "area": "A", "latest_developments": "d", "summary": "s", "tags": [],
             "sources": [{"source": "", "title": "Article Title", "url": "https://x.example/1"}]}]}
        html = generate.render_html(digest, None, [], [], [], self.feeds, "g", "t", "a", "b")
        text = generate.render_text(digest, None, [], [], [], self.feeds, "g", "t")
        self.assertIn(">Article Title</a>", html)
        self.assertIn("- Article Title: https://x.example/1", text)

    def test_health_lines_are_sanitized_and_escaped(self):
        health = {"groups": [], "aux": [{"label": "Scores (ESPN)", "ok": False,
                                        "detail": "no scoreboard; errors: mlb: HTTP 403 <b>‮\x07"}],
                  "cli": {}}
        digest = {"date": TODAY, "headline": "H", "emerging_trends": [], "topics": []}
        html = generate.render_html(digest, None, [], [], [], self.feeds, "g", "t", "a", "b",
                                    health=health)
        self.assertIn("HTTP 403 &lt;b&gt;", html)
        self.assertNotIn("<b>", html.split("Feed Health")[1])
        text = generate.render_text(digest, None, [], [], [], self.feeds, "g", "t", health=health)
        self.assertIn("HTTP 403 <b>", text)

    def test_clean_sports_normalizes_missing_fields(self):
        blocks = generate._clean_sports([{"team": None, "record": None,
                                          "games": [{"date": None, "result": None, "url": None}],
                                          "next": None, "headlines": ["x"]}, "junk"])
        self.assertEqual(blocks, [{"team": "", "record": "", "next": None, "source": "",
                                   "games": [{"date": "", "result": "", "url": "", "recap": ""}]}])
        html = generate._sports_section(blocks, {"around_teams": [local_item("https://p.example/1")]})
        self.assertNotIn("None", "".join(html))
        self.assertNotIn(generate.SCOREBOARD_NOTE, "".join(html))
        self.assertIn(generate.SCOREBOARD_NOTE, "".join(generate._sports_section(
            [], {"around_teams": [local_item("https://p.example/1")]})))

    def test_markets_render_from_one_formatter(self):
        rows = [{"label": "S&P 500", "value": "6,000.00", "pct": "+1.0%", "arrow": "▲"},
                {"label": "Dow", "value": "40,000.00", "pct": "-0.2%", "arrow": "▼"}]
        html = "\n".join(generate._markets_inner(rows))
        self.assertIn("S&amp;P 500  ", html)
        self.assertIn('class="down"', html)
        self.assertEqual(market_data.as_lines(rows)[1], "Dow      40,000.00  ▼ -0.2%")


# ------------------------------------------------------- auxiliary data modules

class MarketData(unittest.TestCase):
    def test_last_bar_dropped_only_while_session_open(self):
        day = int(datetime(2026, 9, 2, tzinfo=timezone.utc).timestamp())  # a UTC midnight
        bar = day + 13 * 3600 + 1800          # 13:30 UTC open
        result = {"meta": {"currentTradingPeriod": {"regular": {"start": bar, "end": bar + 6.5 * 3600}}}}
        self.assertTrue(market_data._session_open(result, bar, bar + 3600))       # mid-session
        self.assertFalse(market_data._session_open(result, bar, bar + 8 * 3600))  # after close, same day
        self.assertFalse(market_data._session_open(result, bar, bar + 86400 * 2))  # older bar
        self.assertTrue(market_data._session_open({}, bar, bar + 8 * 3600))       # no meta: date rule

    def test_weekly_rows_collects_errors(self):
        errors = []
        with mock.patch.object(market_data, "_closes", side_effect=ValueError("nope")):
            rows = market_data.weekly_rows(errors=errors)
        self.assertEqual(rows, [])
        self.assertEqual(len(errors), len(market_data.SYMBOLS))


class Pittsburgh(unittest.TestCase):
    def test_sports_blocks_reports_errors_instead_of_hiding_them(self):
        errors = []
        with mock.patch.object(pittsburgh, "_espn_json", side_effect=RuntimeError("HTTP 403")), \
                mock.patch.object(pittsburgh, "_get_text", side_effect=RuntimeError("HTTP 503")):
            blocks = pittsburgh.sports_blocks(errors=errors)
        self.assertEqual(blocks, [])
        # one ESPN and one plaintextsports failure per league, in that order
        self.assertEqual(len(errors), 2 * len(pittsburgh.LEAGUES))
        self.assertIn("HTTP 403", errors[0])
        self.assertIn("plaintextsports: HTTP 503", errors[1])

    def test_espn_http_error_message_carries_status_not_body(self):
        import urllib.error
        headers = email.message.Message()
        headers["Server"] = "AkamaiGHost"
        err = urllib.error.HTTPError("https://site.api.espn.com/x", 403, "Forbidden", headers,
                                     io.BytesIO(b"<html>Access Denied <script>evil()</script></html>"))
        with mock.patch.object(pittsburgh, "_get_json", side_effect=err):
            with self.assertRaises(RuntimeError) as ctx:
                pittsburgh._espn_json("/baseball/mlb/teams/pit")
        self.assertEqual(str(ctx.exception), "HTTP 403 (server: AkamaiGHost)")

    def test_plaintextsports_urls(self):
        when = datetime(2026, 9, 5, 19, 5, tzinfo=pittsburgh.TZ)
        self.assertEqual(pittsburgh._pts_url("mlb", when, "PIT", "CHW"),
                         "https://plaintextsports.com/mlb/2026-09-05/pit-cws")
        event = {"season": {"year": 2026, "type": 2}, "week": {"number": 1}}
        self.assertEqual(pittsburgh._pts_url("nfl", when, "PIT", "WSH", event),
                         "https://plaintextsports.com/nfl/2026/week1/pit-was")
        self.assertEqual(pittsburgh._pts_url("nfl", when, "PIT", "WSH", {}),
                         "https://plaintextsports.com/nfl/")


# ------------------------------------------------------------ end to end (main)

SEC_FEED_TWO = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
                b'<item><title>Exchange servers exposed</title><link>https://sec.example/1</link>'
                b'<pubDate>%s</pubDate><description>desc one</description></item>'
                b'<item><title>Second story</title><link>https://sec.example/2</link>'
                b'<pubDate>%s</pubDate><description>desc two</description></item>'
                b'</channel></rss>')
SEC_FEED_ONE = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
                b'<item><title>Exchange servers exposed</title><link>https://sec.example/1</link>'
                b'<pubDate>%s</pubDate><description>desc one</description></item>'
                b'</channel></rss>')
PGH_FEED = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
            b'<item><title>Council passes budget</title><link>https://pgh.example/1</link>'
            b'<pubDate>%s</pubDate><description>local</description></item></channel></rss>')


class EndToEnd(TempSite):
    """Drive main() with in-memory feeds, stubbed data sources, a canned model
    and a frozen clock, then run it a second time to exercise carry-forward
    (including a carried source that has left the fetch window) and the
    failed-local-call fallback."""

    @staticmethod
    def sports_blocks(errors=None, notes=None):
        """ESPN is blocked; the Pirates recover through the plaintextsports
        page saved on 2026-09-02, the other two leagues are off-season."""
        page = (Path(__file__).parent / "testdata" / "pts" / "pirates.html").read_text(encoding="utf-8")
        notes.append("mlb: ESPN failed (HTTP 403 (server: AkamaiGHost)); used plaintextsports")
        return [plaintextsports.parse_team_page(
            page, "mlb", datetime(2026, 9, 2, 10, 35, tzinfo=plaintextsports.TZ))]

    def setUp(self):
        super().setUp()
        stamp = (NOW - timedelta(hours=1)).strftime("%a, %d %b %Y %H:%M:%S GMT").encode()
        feeds = {"security": [{"name": "Sec A", "url": "https://sec.example/feed"},
                              {"name": "Sec B", "url": "https://secb.example/feed"},
                              {"name": "Sec Down", "url": "https://down.example/feed"}],
                 "pittsburgh": [{"name": "TribLive", "url": "https://pgh.example/feed"}],
                 "bizpol": [], "events": [], "sports_media": [], "team_usa": [],
                 "reading": [{"name": "Ed Zitron", "url": "https://z.example/feed"}]}
        self.bodies = {"https://sec.example/feed": (SEC_FEED_TWO % (stamp, stamp), None),
                       "https://secb.example/feed": (SEC_FEED_TWO % (stamp, stamp), None),
                       "https://pgh.example/feed": (PGH_FEED % stamp, None),
                       "https://z.example/feed": (PGH_FEED.replace(b"pgh.example", b"z.example") % stamp, None)}
        self.stamp = stamp

        def http_get(url):
            if url not in self.bodies:
                raise OSError("connection refused")
            return self.bodies[url]

        self.prompts = []
        self.fail_local = False

        def run_claude(cli, prompt, timeout=None):
            self.prompts.append(prompt)
            if "BUSINESS_POLITICS_ITEMS" in prompt:
                if self.fail_local:
                    raise RuntimeError("claude CLI exited 1: simulated outage")
                reply = {"business": [{"title": "Budget Passes", "latest_developments": "Council voted",
                                       "summary": "s", "sources": [{"url": "https://pgh.example/1"}]}],
                         "reading": [{"author": "Ed Zitron", "title": "Post", "url": "https://z.example/1",
                                      "summary": "argues"}]}
            elif "STORIES:" in prompt:
                anchor = generate.item_anchor("https://sec.example/1")
                reply = {"entries": [{"kind": "Trend", "text": "Exchange servers everywhere",
                                      "links": [{"anchor": anchor, "phrase": "Exchange"}]}]}
            else:
                reply = {"headline": "Exchange servers exposed", "emerging_trends": [
                    {"text": "Patch Exchange now", "topic_title": "Exchange Exposure", "link_phrase": "Exchange"}],
                    "topics": [{"title": "Exchange Exposure", "area": "Vulnerabilities",
                                "latest_developments": "22,000 servers exposed", "summary": "Patch.",
                                "tags": ["patch"],
                                "sources": [{"source": "x", "url": "https://sec.example/1"},
                                            {"source": "x", "url": "https://sec.example/2"}]}]}
                if "TODAY_SO_FAR —" in prompt:
                    # Run 2 splits the second (carried) source out as its own story;
                    # by then https://sec.example/2 is no longer in any feed body.
                    reply["topics"][0]["sources"] = [{"url": "https://sec.example/1"}]
                    reply["topics"].append({"title": "Second Story", "area": "Other",
                                            "latest_developments": "d", "summary": "s", "tags": [],
                                            "sources": [{"url": "https://sec.example/2"}]})
            return json.dumps(reply), {"models": ["claude-test"], "usage": {"claude-test": {"outputTokens": 5}},
                                       "cost_usd": 0.01, "duration_ms": 10}

        self.patches = [
            mock.patch.object(generate, "datetime", FrozenDatetime),
            mock.patch.object(generate, "load_feeds", lambda: feeds),
            mock.patch.object(generate, "http_get", http_get),
            mock.patch.object(generate, "run_claude", run_claude),
            mock.patch.object(generate, "find_claude_cli", lambda: "/bin/claude"),
            mock.patch.object(generate.market_data, "weekly_rows",
                              lambda errors=None: [{"label": "Dow", "value": "1.00", "pct": "+0.0%", "arrow": "="}]),
            mock.patch.object(generate.pgh_data, "weather_lines", lambda: ["Today: Sunny, high 80F."]),
            mock.patch.object(generate.pgh_data, "sports_blocks", self.sports_blocks),
            mock.patch.object(generate.time, "sleep", lambda s: None),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        generate._RUN_DEADLINE = None
        super().tearDown()

    def test_two_runs_carry_forward_and_survive_a_local_outage(self):
        generate.main()
        today = NOW.astimezone().strftime("%Y-%m-%d")
        rec = json.loads((self.tmp / "data" / f"{today}.json").read_text())
        self.assertEqual([t["title"] for t in rec["topics"]], ["Exchange Exposure"])
        self.assertEqual([s["source"] for s in rec["topics"][0]["sources"]], ["Sec A", "Sec A"])
        self.assertEqual(rec["local"]["business"][0]["title"], "Budget Passes")
        self.assertEqual(rec["meta"]["served_by"], ["claude-test"])
        self.assertEqual(rec["meta"]["model_calls"], 3)
        self.assertEqual(rec["meta"]["feed_failures"], ["Sec Down"])
        sec = next(g for g in rec["feed_health"]["groups"] if g["group"] == "security")
        self.assertEqual((sec["loaded"], sec["feeds"], sec["in_window"]), (2, 3, 2))
        self.assertEqual(sec["failed"][0]["name"], "Sec Down")
        self.assertEqual(sec["empty"], [])  # Sec B duplicates Sec A's headlines but is not silent
        scores = next(a for a in rec["feed_health"]["aux"] if a["label"].startswith("Scores"))
        # the Pirates came from the fallback (recovered, ok) and the NHL from nowhere
        self.assertTrue(scores["ok"])
        self.assertIn("1 team via plaintextsports", scores["detail"])
        self.assertIn("mlb: ESPN failed (HTTP 403 (server: AkamaiGHost)); used plaintextsports",
                      scores["detail"])
        self.assertNotIn("errors:", scores["detail"])
        self.assertEqual(rec["sports"][0]["source"], "plaintextsports")
        self.assertEqual(rec["sports"][0]["games"][0]["result"], "Giants 12 · Pirates 13 · Final")
        self.assertNotIn("as_of", rec["sports"][0])  # health-only keys never reach the record
        self.assertTrue(any(n.startswith("Quiet day") for n in rec["notes"]))
        html = (self.tmp / "index.html").read_text()
        self.assertIn("HTTP 403", html)  # the ESPN failure stays visible in Feed Health
        self.assertIn("Giants 12 · Pirates 13 · Final", html)
        self.assertIn('href="https://plaintextsports.com/mlb/2026-09-01/sf-pit"', html)
        self.assertNotIn("; ; and", html)  # empty feed groups do not leave holes in the footer
        self.assertNotIn("TODAY_SO_FAR —", self.prompts[0])
        local_prompt = next(p for p in self.prompts if "BUSINESS_POLITICS_ITEMS" in p)
        self.assertNotIn("TODAY_SO_FAR_LOCAL —", local_prompt)

        # Second run of the day: sec.example/2 has left every feed, so "Second
        # Story" can only be cited through the carried record; the local call fails.
        self.prompts.clear()
        self.fail_local = True
        self.bodies["https://sec.example/feed"] = (SEC_FEED_ONE % self.stamp, None)
        self.bodies["https://secb.example/feed"] = (SEC_FEED_ONE % self.stamp, None)
        generate.main()
        sec_prompt = next(p for p in self.prompts if "Cluster them" in p)
        self.assertIn("TODAY_SO_FAR —", sec_prompt)
        self.assertIn("Exchange Exposure", sec_prompt)
        local_prompt = next(p for p in self.prompts if "BUSINESS_POLITICS_ITEMS" in p)
        self.assertIn("TODAY_SO_FAR_LOCAL —", local_prompt)
        self.assertIn("Budget Passes", local_prompt)
        self.assertIn("Carry forward EVERY item", local_prompt)
        rec2 = json.loads((self.tmp / "data" / f"{today}.json").read_text())
        self.assertEqual([t["title"] for t in rec2["topics"]], ["Exchange Exposure", "Second Story"])
        self.assertEqual(rec2["topics"][1]["sources"],
                         [{"source": "Sec A", "title": "", "url": "https://sec.example/2"}])
        self.assertEqual(rec2["local"]["business"][0]["title"], "Budget Passes")  # kept, not null
        self.assertTrue(rec2["meta"]["local_from"])
        self.assertTrue(any("carried over" in n for n in rec2["notes"]))
        self.assertIn("carried over", (self.tmp / "digest.txt").read_text())
        glance = rec2["glance"]
        self.assertTrue(glance and glance[0]["links"][0]["anchor"] == generate.item_anchor("https://sec.example/1"))

    def test_run_aborts_without_security_feeds(self):
        self.bodies = {k: v for k, v in self.bodies.items() if "sec" not in k}
        with self.assertRaises(SystemExit) as ctx:
            generate.main()
        self.assertIn("security feeds", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
