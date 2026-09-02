"""Tests for the infosecfollow engine (engine/generate.py and friends).

Run from the repository root:

    python3 -m unittest discover -s engine -p 'test_*.py'

No network and no model: feeds are in-memory bytes, the Claude CLI is a stub,
and the site is written to a temporary directory. The committed day records
under docs/data/ double as renderer fixtures.
"""

import json
import os
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

NOW = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
TODAY = "2026-09-02"
REPO_DOCS = Path(__file__).resolve().parent.parent / "docs"


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

    def test_latin1_body_without_declaration_uses_http_charset(self):
        raw = ("<rss version=\"2.0\"><channel><item><title>Caf\xe9</title>"
               "<link>https://x.example/a</link></item></channel></rss>").encode("latin-1")
        items = list(generate.parse_feed("f", raw, charset="iso-8859-1"))
        self.assertEqual(items[0]["title"], "Café")

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


# ------------------------------------------------------------------ validation

def digest_reply(sources):
    return {"headline": "Head", "emerging_trends": [{"text": "trend", "topic_title": "T"}],
            "topics": [{"title": "T", "area": "A", "latest_developments": "new",
                        "summary": "sum", "tags": ["x", "", 3, "Y"], "sources": sources}]}


class DigestValidation(unittest.TestCase):
    ALLOWED = {"https://ok.example/1": "Feed One", "https://ok.example/2": "Feed Two"}

    def test_sources_canonical_deduped_and_capped(self):
        reply = digest_reply([{"source": "Reworded", "url": "https://ok.example/1", "title": "t"},
                              {"source": "x", "url": "https://ok.example/1"},
                              {"source": "x", "url": "https://bad.example/1"},
                              {"source": "x", "url": "https://ok.example/2"}])
        out = generate.validate_digest(reply, self.ALLOWED)
        self.assertEqual([s["source"] for s in out["topics"][0]["sources"]], ["Feed One", "Feed Two"])
        self.assertEqual(out["topics"][0]["tags"], ["x", "y"])

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
        pgh = {f"https://pgh.example/{n}": "TribLive" for n in range(10)}
        self.allowed = {"business_politics": {"https://wsj.example/1": "WSJ"},
                        "business": pgh, "around_town": pgh, "events": pgh,
                        "around_teams": {"https://pg.example/1": "PG Steelers"},
                        "team_usa": {}, "reading": {"https://z.example/1": "Ed Zitron",
                                                    "https://z.example/2": "Ed Zitron",
                                                    "https://s.example/1": "Stratechery"}}
        self.authors = ["Ed Zitron", "Stratechery", "Cal Newport"]

    def validate(self, reply, strict=True):
        return generate.validate_local(reply, self.allowed, True, True, self.authors, strict)

    def test_caps_violence_filter_and_reading_rules(self):
        reply = {
            "business": [local_item(f"https://pgh.example/{n}", f"B{n}") for n in range(8)],
            "around_town": [local_item("https://pgh.example/1", "Shooting on Penn Avenue",
                                       "Police said the man was fatally shot"),
                            local_item("https://pgh.example/2", "Budget", "Council passed it")],
            "reading": [{"author": "ed zitron", "title": "A", "url": "https://z.example/1", "summary": "s"},
                        {"author": "Ed Zitron", "title": "B", "url": "https://z.example/2", "summary": "s"},
                        {"author": "Nobody", "title": "C", "url": "https://s.example/1", "summary": "s"}],
        }
        out = self.validate(reply)
        self.assertEqual(len(out["business"]), generate.SECTION_CAPS["business"])
        self.assertEqual([i["title"] for i in out["around_town"]], ["Budget"])
        self.assertEqual([(r["author"], r["title"]) for r in out["reading"]], [("Ed Zitron", "A")])
        self.assertEqual(out["business"][0]["sources"][0]["source"], "TribLive")
        self.assertEqual(out["events"], [])  # omitted key becomes an empty list

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

    def tearDown(self):
        generate._CLI_HELP.clear()

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
        self.assertFalse(os.path.exists(seen["cwd"]))  # scratch dir removed

    def test_ask_claude_retries_process_failures_with_backoff(self):
        calls = {"n": 0}

        def flaky(cli, prompt):
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

    def test_ask_claude_gives_up_after_attempts(self):
        with mock.patch.object(generate, "run_claude",
                               mock.Mock(side_effect=RuntimeError("down"))), \
                mock.patch.object(generate.time, "sleep", lambda s: None):
            with self.assertRaises(RuntimeError):
                generate.ask_claude("/bin/claude", "p", lambda d, strict: d)

    def test_ask_claude_repairs_once_then_relaxes(self):
        prompts, strict_flags = [], []

        def run(cli, prompt):
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

        def run(cli, prompt):
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
        self.assertIn("TODAY_SO_FAR", generate.build_prompt([], 24, TODAY, prior, carried))
        self.assertIsNone(generate.today_so_far("2026-09-03"))

    def test_lookback_is_independent_of_retention(self):
        self.write_record("2026-09-01")
        with mock.patch.object(generate, "ARCHIVE_RETENTION_DAYS", 0):
            dated = generate._archive_dates_within(TODAY, generate.PRIOR_LOOKBACK_DAYS)
        self.assertEqual([d for _, d in dated], ["2026-09-01"])

    def test_prune_off_by_default_and_bounded_when_on(self):
        for d in ("2026-05-01", "2026-09-01"):
            self.write_record(d)
            (self.tmp / "archive" / f"{d}-0705.html").write_text("x")
        self.assertEqual(generate.ARCHIVE_RETENTION_DAYS, 0)
        generate.prune_old_archives(TODAY, 0)
        self.assertTrue((self.tmp / "data" / "2026-05-01.json").exists())
        generate.prune_old_archives(TODAY, 30)
        self.assertFalse((self.tmp / "data" / "2026-05-01.json").exists())
        self.assertFalse((self.tmp / "archive" / "2026-05-01-0705.html").exists())
        self.assertTrue((self.tmp / "data" / "2026-09-01.json").exists())


class SiteWriting(TempSite):
    def test_write_site_is_atomic_and_records_everything(self):
        digest = {"date": TODAY, "headline": "Head", "emerging_trends": [],
                  "topics": [{"title": "T", "area": "A", "latest_developments": "d",
                              "summary": "s", "tags": [], "sources": [{"source": "F", "url": "https://x.example/1"}]}]}
        health = {"groups": [], "aux": [{"label": "Scores (ESPN)", "ok": False, "detail": "no scoreboard"}],
                  "cli": {"models": ["m"], "calls": 1, "cost_usd": 0.1, "duration_ms": 1000}}
        feeds = generate.load_feeds()
        generate.write_site(digest, None, [], [], [], feeds, 5, 24, glance=[],
                            notes=["Quiet day"], health=health, meta_extra={"served_by": ["m"]})
        rec = json.loads((self.tmp / "data" / f"{TODAY}.json").read_text())
        self.assertEqual(rec["feed_health"]["aux"][0]["label"], "Scores (ESPN)")
        self.assertEqual(rec["meta"]["served_by"], ["m"])
        self.assertEqual(rec["notes"], ["Quiet day"])
        self.assertIn("glance", rec)
        self.assertEqual([p.name for p in self.tmp.glob("*.tmp")], [])
        html = (self.tmp / "index.html").read_text()
        self.assertIn("Feed Health", html)
        self.assertIn("Quiet day", html)
        self.assertIn("<main", html)
        self.assertIn('rel="canonical"', html)
        self.assertEqual(len(list((self.tmp / "archive").glob("*.html"))), 2)  # page + index
        archive_page = next(p for p in (self.tmp / "archive").glob("*.html") if p.stem != "index")
        self.assertNotIn('rel="canonical"', archive_page.read_text())
        self.assertIn("FEED HEALTH", (self.tmp / "digest.txt").read_text())


# ------------------------------------------------------------------- rendering

class Rendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.feeds = generate.load_feeds()
        cls.records = []
        for path in sorted((REPO_DOCS / "data").glob("*.json"))[-20:]:
            rec = json.loads(path.read_text(encoding="utf-8"))
            if rec.get("topics") and "latest_developments" in rec["topics"][0]:
                cls.records.append(rec)

    def render(self, rec, depth=0):
        digest = {k: rec[k] for k in ("date", "headline", "emerging_trends", "topics")}
        local = rec.get("local")
        generate.assign_anchors(digest, local)
        sports = generate._clean_sports(rec.get("sports") or [])
        html = generate.render_html(digest, local, rec.get("markets") or [], rec.get("weather") or [],
                                    sports, self.feeds, "2026-09-01 19:35 EDT", "7:35 PM EDT",
                                    "archive/index.html", "digest.txt", depth=depth,
                                    glance=rec.get("glance") or [], health=rec.get("feed_health"))
        text = generate.render_text(digest, local, rec.get("markets") or [], rec.get("weather") or [],
                                    sports, self.feeds, "2026-09-01 19:35 EDT", "7:35 PM EDT",
                                    glance=rec.get("glance") or [], health=rec.get("feed_health"))
        return html, text

    def test_committed_records_render_valid_html_with_sound_outline(self):
        self.assertGreater(len(self.records), 5)
        for rec in self.records:
            html, text = self.render(rec)
            p = OutlineParser()
            p.feed(html)
            self.assertEqual((p.stack, p.errors), ([], []), rec["date"])
            for a, b in zip(p.headings, p.headings[1:]):
                self.assertLessEqual(b, a + 1, f"{rec['date']}: heading jumps {a} -> {b}")
            self.assertEqual(len(p.ids), len(set(p.ids)), f"{rec['date']}: duplicate ids")
            self.assertIn('class="skip"', html)
            self.assertIn("Jump to:", html)
            self.assertIn("CONTENTS:", text)
            for topic in rec["topics"]:
                self.assertIn(topic["title"].upper()[:20], text)

    def test_every_in_page_link_has_a_target(self):
        for rec in self.records:
            html, _ = self.render(rec)
            p = OutlineParser()
            p.feed(html)
            targets = set(p.ids)
            import re
            for m in re.finditer(r'href="#([^"]+)"', html):
                self.assertIn(m.group(1), targets, rec["date"])

    def test_source_label_fallback_matches_between_renditions(self):
        digest = {"date": TODAY, "headline": "H", "emerging_trends": [], "topics": [
            {"title": "T", "area": "A", "latest_developments": "d", "summary": "s", "tags": [],
             "sources": [{"source": "", "title": "Article Title", "url": "https://x.example/1"}]}]}
        html = generate.render_html(digest, None, [], [], [], self.feeds, "g", "t", "a", "b")
        text = generate.render_text(digest, None, [], [], [], self.feeds, "g", "t")
        self.assertIn(">Article Title</a>", html)
        self.assertIn("- Article Title: https://x.example/1", text)

    def test_clean_sports_normalizes_missing_fields(self):
        blocks = generate._clean_sports([{"team": None, "record": None,
                                          "games": [{"date": None, "result": None, "url": None}],
                                          "next": None, "headlines": ["x"]}, "junk"])
        self.assertEqual(blocks, [{"team": "", "record": "", "next": None,
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
        with mock.patch.object(pittsburgh, "_espn_json", side_effect=RuntimeError("HTTP 403 Forbidden")):
            blocks = pittsburgh.sports_blocks(errors=errors)
        self.assertEqual(blocks, [])
        self.assertEqual(len(errors), len(pittsburgh.LEAGUES))
        self.assertIn("HTTP 403", errors[0])

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

SEC_FEED = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
            b'<item><title>Exchange servers exposed</title><link>https://sec.example/1</link>'
            b'<pubDate>%s</pubDate><description>desc one</description></item>'
            b'<item><title>Second story</title><link>https://sec.example/2</link>'
            b'<pubDate>%s</pubDate><description>desc two</description></item>'
            b'</channel></rss>')
PGH_FEED = (b'<?xml version="1.0"?><rss version="2.0"><channel>'
            b'<item><title>Council passes budget</title><link>https://pgh.example/1</link>'
            b'<pubDate>%s</pubDate><description>local</description></item></channel></rss>')


class EndToEnd(TempSite):
    """Drive main() with in-memory feeds, stubbed data sources, and a canned
    model, then run it a second time to exercise carry-forward and the
    failed-local-call fallback."""

    def setUp(self):
        super().setUp()
        stamp = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT").encode()
        feeds = {"security": [{"name": "Sec A", "url": "https://sec.example/feed"},
                              {"name": "Sec B", "url": "https://secb.example/feed"},
                              {"name": "Sec Down", "url": "https://down.example/feed"}],
                 "pittsburgh": [{"name": "TribLive", "url": "https://pgh.example/feed"}],
                 "bizpol": [], "events": [], "sports_media": [], "team_usa": [],
                 "reading": [{"name": "Ed Zitron", "url": "https://z.example/feed"}]}
        bodies = {"https://sec.example/feed": (SEC_FEED % (stamp, stamp), None),
                  "https://secb.example/feed": (SEC_FEED % (stamp, stamp), None),
                  "https://pgh.example/feed": (PGH_FEED % stamp, None),
                  "https://z.example/feed": (PGH_FEED.replace(b"pgh.example", b"z.example") % stamp, None)}

        def http_get(url):
            if url not in bodies:
                raise OSError("connection refused")
            return bodies[url]

        self.prompts = []
        self.fail_local = False

        def run_claude(cli, prompt):
            self.prompts.append(prompt)
            if "BUSINESS_POLITICS_ITEMS" in prompt:
                if self.fail_local:
                    raise RuntimeError("claude CLI exited 1: simulated outage")
                reply = {"business": [{"title": "Budget Passes", "latest_developments": "Council voted",
                                       "summary": "s", "sources": [{"url": "https://pgh.example/1"}]}],
                         "reading": [{"author": "Ed Zitron", "title": "Post", "url": "https://z.example/1",
                                      "summary": "argues"}]}
            elif "STORIES:" in prompt:
                reply = {"entries": [{"kind": "Trend", "text": "Exchange servers everywhere",
                                      "links": [{"anchor": "__ANCHOR__", "phrase": "Exchange"}]}]}
                anchor = generate.item_anchor("https://sec.example/1")
                reply = json.loads(json.dumps(reply).replace("__ANCHOR__", anchor))
            else:
                reply = {"headline": "Exchange servers exposed", "emerging_trends": [
                    {"text": "Patch Exchange now", "topic_title": "Exchange Exposure", "link_phrase": "Exchange"}],
                    "topics": [{"title": "Exchange Exposure", "area": "Vulnerabilities",
                                "latest_developments": "22,000 servers exposed", "summary": "Patch.",
                                "tags": ["patch"], "sources": [{"source": "x", "url": "https://sec.example/1"}]}]}
                if "TODAY_SO_FAR" in prompt:
                    reply["topics"].append({"title": "Second Story", "area": "Other",
                                            "latest_developments": "d", "summary": "s", "tags": [],
                                            "sources": [{"url": "https://sec.example/2"}]})
            return json.dumps(reply), {"models": ["claude-test"], "usage": {"claude-test": {"outputTokens": 5}},
                                       "cost_usd": 0.01, "duration_ms": 10}

        self.patches = [
            mock.patch.object(generate, "load_feeds", lambda: feeds),
            mock.patch.object(generate, "http_get", http_get),
            mock.patch.object(generate, "run_claude", run_claude),
            mock.patch.object(generate, "find_claude_cli", lambda: "/bin/claude"),
            mock.patch.object(generate.market_data, "weekly_rows",
                              lambda errors=None: [{"label": "Dow", "value": "1.00", "pct": "+0.0%", "arrow": "="}]),
            mock.patch.object(generate.pgh_data, "weather_lines", lambda: ["Today: Sunny, high 80F."]),
            mock.patch.object(generate.pgh_data, "sports_blocks",
                              lambda errors=None: errors.append("mlb: HTTP 403 Forbidden") or []),
            mock.patch.object(generate.time, "sleep", lambda s: None),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        super().tearDown()

    def test_two_runs_carry_forward_and_survive_a_local_outage(self):
        generate.main()
        today = datetime.now().astimezone().strftime("%Y-%m-%d")
        rec = json.loads((self.tmp / "data" / f"{today}.json").read_text())
        self.assertEqual([t["title"] for t in rec["topics"]], ["Exchange Exposure"])
        self.assertEqual(rec["topics"][0]["sources"][0]["source"], "Sec A")  # canonical outlet
        self.assertEqual(rec["local"]["business"][0]["title"], "Budget Passes")
        self.assertEqual(rec["meta"]["served_by"], ["claude-test"])
        self.assertEqual(rec["meta"]["model_calls"], 3)
        self.assertEqual(rec["meta"]["feed_failures"], ["Sec Down"])
        sec = next(g for g in rec["feed_health"]["groups"] if g["group"] == "security")
        self.assertEqual((sec["loaded"], sec["feeds"], sec["in_window"]), (2, 3, 2))
        self.assertEqual(sec["failed"][0]["name"], "Sec Down")
        scores = next(a for a in rec["feed_health"]["aux"] if a["label"].startswith("Scores"))
        self.assertIn("HTTP 403", scores["detail"])
        self.assertTrue(any(n.startswith("Quiet day") for n in rec["notes"]))
        html = (self.tmp / "index.html").read_text()
        self.assertIn("HTTP 403", html)  # ESPN failure is visible in Feed Health
        self.assertNotIn("; ; and", html)  # empty feed groups do not leave holes in the footer
        self.assertNotIn("TODAY_SO_FAR", self.prompts[0])

        # Second run of the day: carry-forward block present, local call fails.
        self.prompts.clear()
        self.fail_local = True
        generate.main()
        sec_prompt = next(p for p in self.prompts if "Cluster them" in p)
        self.assertIn("TODAY_SO_FAR", sec_prompt)
        self.assertIn("Exchange Exposure", sec_prompt)
        rec2 = json.loads((self.tmp / "data" / f"{today}.json").read_text())
        self.assertEqual([t["title"] for t in rec2["topics"]], ["Exchange Exposure", "Second Story"])
        self.assertEqual(rec2["local"]["business"][0]["title"], "Budget Passes")  # kept, not null
        self.assertTrue(rec2["meta"]["local_from"])
        self.assertTrue(any("carried over" in n for n in rec2["notes"]))
        self.assertIn("carried over", (self.tmp / "digest.txt").read_text())
        glance = rec2["glance"]
        self.assertTrue(glance and glance[0]["links"][0]["anchor"] == generate.item_anchor("https://sec.example/1"))


if __name__ == "__main__":
    unittest.main()
