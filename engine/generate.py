#!/usr/bin/env python3
"""infosecfollow engine.

Daily pipeline: fetch security RSS/Atom feeds -> keep the last 24h of items ->
ask Claude (headless `claude -p`) to cluster them into trending topics with
summaries -> render the static site (plain-text HTML + .txt + .json archive).

Stdlib only. Run:  python3 engine/generate.py
"""

import glob
import gzip
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree

ENGINE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ENGINE_DIR.parent
SITE_DIR = PROJECT_DIR / "docs"  # "docs" because GitHub Pages serves main:/docs

USER_AGENT = "infosecfollow/1.0 (RSS aggregator)"
FETCH_TIMEOUT = 25          # per-feed seconds
MAX_FEED_BYTES = 8 * 1024 * 1024  # cap per feed, before and after gzip
FUTURE_SLACK_HOURS = 2      # tolerate this much clock skew in item dates
TEXT_WIDTH = 64             # wrap column for digest.txt
WINDOW_HOURS = 24           # primary lookback window
FALLBACK_WINDOW_HOURS = 48  # widen to this if too few items
MIN_ITEMS = 12              # threshold that triggers the wider window
MAX_ITEMS = 120             # cap on corpus size sent to the model
SUMMARY_CHARS = 480         # per-item summary truncation
MODEL = os.environ.get("INFOSECFOLLOW_MODEL", "claude-opus-4-8")
CLI_TIMEOUT = 900           # seconds for the summarization call


# --------------------------------------------------------------------------- fetch

def load_feeds():
    with open(ENGINE_DIR / "feeds.json", encoding="utf-8") as f:
        return json.load(f)["feeds"]


def http_get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    })
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
        raw = resp.read(MAX_FEED_BYTES + 1)
        if len(raw) > MAX_FEED_BYTES:
            raise ValueError(f"response larger than {MAX_FEED_BYTES} bytes")
        if resp.headers.get("Content-Encoding", "").lower() == "gzip" or raw[:2] == b"\x1f\x8b":
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
                raw = gz.read(MAX_FEED_BYTES + 1)
            if len(raw) > MAX_FEED_BYTES:
                raise ValueError(f"decompressed response larger than {MAX_FEED_BYTES} bytes")
        return raw


def _local(tag):
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _child_text(elem, *names):
    for child in elem:
        if _local(child.tag) in names and (child.text or "").strip():
            return child.text.strip()
    return ""


def _atom_link(elem):
    fallback = ""
    for child in elem:
        if _local(child.tag) == "link":
            href = child.get("href", "")
            if not href:
                continue
            if child.get("rel", "alternate") == "alternate":
                return href
            fallback = fallback or href
    return fallback


def parse_date(text):
    if not text:
        return None
    text = text.strip()
    try:
        dt = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# Matches plausible HTML tags only, so literal "<" in prose ("versions < 2.4")
# survives. Applied both before unescaping (raw HTML in CDATA) and after
# (HTML that arrived entity-escaped).
_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>|<!--.*?-->", re.DOTALL)
_CTRL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def sanitize(text):
    return _CTRL_RE.sub("", str(text))


def clean_text(text, limit):
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _TAG_RE.sub(" ", text)
    text = sanitize(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[: limit - 3].rsplit(" ", 1)[0] + "..."
    return text


def parse_feed(source_name, raw):
    """Yield item dicts from RSS 2.0, RSS 1.0 (RDF), or Atom bytes."""
    root = ElementTree.fromstring(raw)
    root_name = _local(root.tag)
    if root_name == "rss":
        channel = next((c for c in root if _local(c.tag) == "channel"), None)
        elems = [c for c in channel if _local(c.tag) == "item"] if channel is not None else []
    elif root_name == "RDF":
        elems = [c for c in root if _local(c.tag) == "item"]
    elif root_name == "feed":
        elems = [c for c in root if _local(c.tag) == "entry"]
    else:
        raise ValueError(f"unrecognized feed root <{root_name}>")

    for elem in elems:
        title = clean_text(_child_text(elem, "title"), 250)
        if root_name == "feed":
            link = _atom_link(elem)
        else:
            link = _child_text(elem, "link") or _atom_link(elem)
        published = parse_date(_child_text(elem, "pubDate", "published", "updated", "date"))
        summary = clean_text(_child_text(elem, "description", "summary", "content", "encoded"),
                             SUMMARY_CHARS)
        if title and link:
            yield {
                "source": source_name,
                "title": title,
                "url": link.strip(),
                "published": published,
                "summary": summary,
            }


def fetch_all(feeds):
    items, failures = [], []

    def fetch_one(feed):
        return list(parse_feed(feed["name"], http_get(feed["url"])))

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_one, feed): feed for feed in feeds}
        for future in as_completed(futures):
            feed = futures[future]
            try:
                got = future.result()
                items.extend(got)
                print(f"  ok   {feed['name']}: {len(got)} items")
            except Exception as exc:
                failures.append(feed["name"])
                print(f"  FAIL {feed['name']}: {sanitize(exc)[:300]}")
    return items, failures


def select_window(items, now):
    """Keep items from the last 24h (48h if the day is thin), dedupe, cap."""
    horizon = now + timedelta(hours=FUTURE_SLACK_HOURS)  # drop bogus future dates

    def within(hours):
        cutoff = now - timedelta(hours=hours)
        return [i for i in items if i["published"] and cutoff <= i["published"] <= horizon]

    window = WINDOW_HOURS
    selected = within(window)
    if len(selected) < MIN_ITEMS:
        window = FALLBACK_WINDOW_HOURS
        selected = within(window)

    seen, deduped = set(), []
    for item in sorted(selected, key=lambda i: i["published"], reverse=True):
        key = re.sub(r"\W+", "", item["title"].lower())
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped[:MAX_ITEMS], window


# --------------------------------------------------------------------------- summarize

def find_claude_cli():
    override = os.environ.get("INFOSECFOLLOW_CLAUDE_BIN")
    if override and os.access(override, os.X_OK):
        return override
    on_path = shutil.which("claude")
    if on_path:
        return on_path
    pattern = os.path.expanduser(
        "~/Library/Application Support/Claude/claude-code/*/claude.app/Contents/MacOS/claude")
    def version_key(path):
        version = Path(path).parents[3].name
        return [int(p) if p.isdigit() else 0 for p in version.split(".")]
    candidates = [p for p in glob.glob(pattern) if os.access(p, os.X_OK)]
    if candidates:
        return max(candidates, key=version_key)
    raise RuntimeError(
        "claude CLI not found: set INFOSECFOLLOW_CLAUDE_BIN, install the CLI, "
        "or install the Claude desktop app")


def build_prompt(items, window, today):
    corpus = [
        {
            "source": i["source"],
            "title": i["title"],
            "url": i["url"],
            "published": i["published"].strftime("%Y-%m-%d %H:%M UTC"),
            "summary": i["summary"],
        }
        for i in items
    ]
    return f"""You are the editor of "infosecfollow", a daily plain-text briefing on information security. Below are {len(corpus)} news items published in the last {window} hours by major security outlets, vendors, and government sources, as a JSON array.

Cluster them into the day's trending topics and respond with ONLY a JSON object (no markdown fences, no commentary) in exactly this shape:

{{
  "date": "{today}",
  "headline": "One sentence capturing the most important security story or theme of the day.",
  "emerging_trends": ["3 to 5 entries; each a single sentence naming a trend visible across multiple items and why it matters."],
  "topics": [
    {{
      "title": "Short topic name (a campaign, vulnerability, incident, or theme)",
      "last_24h": "One sentence describing the relevant updates on this topic in the last 24 hours.",
      "summary": "Two to four sentences of plain-text background and analysis: what it is, who is affected, what to do.",
      "tags": ["1-3 lowercase tags like ransomware, zero-day, apt, patch, breach, policy"],
      "sources": [{{"source": "outlet name", "title": "article title", "url": "exact url copied from the items below"}}]
    }}
  ]
}}

Rules:
- 5 to 8 topics, ordered most to least important. Merge near-duplicate coverage of the same story into one topic.
- Each topic cites 1 to 4 sources whose "url" values are copied EXACTLY from the items below. Never invent or modify a URL.
- Plain text only in every field: no markdown, no HTML, no bullet characters.
- Be concrete: name the malware, CVE IDs, vendors, and threat actors that appear in the items. Do not speculate beyond them.
- Skip vendor marketing and product-promo items unless they carry real news.

Items:
{json.dumps(corpus, ensure_ascii=False, indent=1)}
"""


def extract_json(text):
    text = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start:end + 1])


def validate_digest(digest, allowed_urls):
    problems = []
    if not isinstance(digest.get("headline"), str) or not digest.get("headline").strip():
        problems.append("missing headline")
    trends = digest.get("emerging_trends")
    if not isinstance(trends, list) or not all(isinstance(t, str) for t in trends) or not trends:
        problems.append("missing emerging_trends")
    topics = digest.get("topics")
    if not isinstance(topics, list) or not topics:
        problems.append("missing topics")
    else:
        for n, topic in enumerate(topics):
            if not isinstance(topic, dict):
                problems.append(f"topic {n}: must be an object")
                continue
            for key in ("title", "last_24h", "summary"):
                if not isinstance(topic.get(key), str) or not topic.get(key).strip():
                    problems.append(f"topic {n}: missing {key}")
            tags = topic.get("tags")
            topic["tags"] = [t for t in tags if isinstance(t, str)] if isinstance(tags, list) else []
            cited = topic.get("sources")
            cited = cited if isinstance(cited, list) else []
            sources = []
            for src in cited:
                url = src.get("url", "") if isinstance(src, dict) else ""
                if url in allowed_urls:
                    sources.append({
                        "source": str(src.get("source", "")),
                        "title": str(src.get("title", "")),
                        "url": url,
                    })
            topic["sources"] = sources
            if not sources:
                problems.append(
                    f"topic {n}: no valid sources; every topic needs 1-4 sources whose "
                    "url is copied exactly from the provided items")
    if problems:
        raise ValueError("; ".join(problems))
    return digest


# The prompt embeds text from external feeds, so the headless session gets no
# tools, no MCP servers, and no user/project settings, and runs in an empty
# scratch directory. Summarization is pure text-in/text-out.
DISALLOWED_TOOLS = ("Bash,Read,Write,Edit,NotebookEdit,Glob,Grep,WebFetch,WebSearch,"
                    "Task,Agent,TodoWrite,Skill,KillShell,BashOutput,ToolSearch")


def run_claude(cli, prompt):
    scratch = tempfile.mkdtemp(prefix="infosecfollow-")
    try:
        proc = subprocess.run(
            [cli, "-p", "--model", MODEL, "--output-format", "text",
             "--disallowedTools", DISALLOWED_TOOLS,
             "--strict-mcp-config", "--setting-sources", ""],
            input=prompt, capture_output=True, text=True,
            timeout=CLI_TIMEOUT, cwd=scratch,
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI exited {proc.returncode}: "
                           f"{sanitize(proc.stderr.strip())[:500]}")
    return proc.stdout


def summarize(items, window, today):
    cli = find_claude_cli()
    print(f"  using {cli}\n  model {MODEL}, {len(items)} items, {window}h window")
    prompt = build_prompt(items, window, today)
    allowed_urls = {i["url"] for i in items}
    last_error = None
    for attempt in (1, 2):
        try:
            output = run_claude(cli, prompt)
            return validate_digest(extract_json(output), allowed_urls)
        except (ValueError, TypeError, AttributeError, KeyError,
                subprocess.TimeoutExpired) as exc:
            last_error = exc
            print(f"  attempt {attempt} failed: {type(exc).__name__}: {sanitize(exc)[:300]}")
            prompt += ("\n\nIMPORTANT: your previous reply was rejected "
                       f"({sanitize(exc)[:300]}). Respond again with ONLY a single valid "
                       "JSON object in the required shape, nothing else.")
    raise RuntimeError(f"model never produced a valid digest: {last_error}")


# --------------------------------------------------------------------------- render

def esc(text):
    return html.escape(str(text), quote=True)


def safe_url(url):
    return esc(url) if url.startswith(("http://", "https://")) else "#"


PAGE_CSS = """
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body { margin: 0 auto; padding: 1.25rem 1rem 3rem; max-width: 44rem;
         font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
         font-size: 15px; line-height: 1.6; overflow-wrap: break-word;
         background: #fdfdfa; color: #1c1c1a; }
  @media (prefers-color-scheme: dark) { body { background: #161614; color: #d8d8d2; } }
  header h1 { font-size: 1.3rem; margin: 0; letter-spacing: 0.04em; }
  header p, footer { font-size: 0.85rem; opacity: 0.75; }
  hr { border: 0; border-top: 1px solid currentColor; opacity: 0.25; margin: 1.5rem 0; }
  h2 { font-size: 1rem; text-transform: uppercase; letter-spacing: 0.08em; margin: 2rem 0 0.75rem; }
  h3 { font-size: 1rem; margin: 1.75rem 0 0.25rem; }
  ul { padding-left: 1.25rem; margin: 0.5rem 0; }
  li { margin: 0.4rem 0; }
  p { margin: 0.5rem 0; }
  a { color: inherit; }
  .updated { font-style: italic; }
  .tags { font-size: 0.8rem; opacity: 0.7; }
  .sources { font-size: 0.85rem; margin-top: 0.4rem; }
  .sources a { overflow-wrap: anywhere; }
  .headline { font-size: 1.05rem; font-weight: bold; margin-top: 1rem; }
  nav { font-size: 0.85rem; margin-top: 0.25rem; }
"""


def render_html(digest, feeds, generated_at, archive_href, text_href, depth=0):
    prefix = "../" * depth
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>infosecfollow — {esc(digest['date'])}</title>",
        f"<style>{PAGE_CSS}</style>",
        "</head>",
        "<body>",
        "<header>",
        f'<h1><a href="{prefix}index.html" style="text-decoration:none">infosecfollow</a></h1>',
        "<p>daily plain-text briefing on trending topics in security</p>",
        f"<nav>{esc(digest['date'])} &middot; <a href=\"{archive_href}\">archive</a> &middot; "
        f"<a href=\"{text_href}\">plain text</a></nav>",
        "</header>",
        f'<p class="headline">{esc(digest["headline"])}</p>',
        "<hr>",
        "<h2>Emerging trends</h2>",
        "<ul>",
    ]
    parts += [f"<li>{esc(trend)}</li>" for trend in digest["emerging_trends"]]
    parts.append("</ul>")
    parts.append("<h2>Topics</h2>")
    for n, topic in enumerate(digest["topics"], 1):
        parts.append(f"<h3>{n}. {esc(topic['title'])}</h3>")
        if topic["tags"]:
            parts.append(f'<p class="tags">[{esc(", ".join(topic["tags"]))}]</p>')
        parts.append(f'<p class="updated">Last 24h: {esc(topic["last_24h"])}</p>')
        parts.append(f"<p>{esc(topic['summary'])}</p>")
        if topic["sources"]:
            links = " &middot; ".join(
                f'<a href="{safe_url(s["url"])}">{esc(s["source"] or s["title"] or "source")}</a>'
                for s in topic["sources"])
            parts.append(f'<p class="sources">Sources: {links}</p>')
    parts += [
        "<hr>",
        "<footer>",
        f"<p>Generated {esc(generated_at)} from {len(feeds)} feeds: "
        f"{esc(', '.join(f['name'] for f in feeds))}.</p>",
        "<p>Summaries are AI-generated from the linked reporting; verify details at the sources.</p>",
        "</footer>",
        "</body></html>",
    ]
    return "\n".join(parts)


def _fill(text, initial="", subsequent=None):
    return textwrap.fill(text, width=TEXT_WIDTH, initial_indent=initial,
                         subsequent_indent=initial if subsequent is None else subsequent,
                         break_long_words=False, break_on_hyphens=False)


def render_text(digest, feeds, generated_at):
    bar = "=" * TEXT_WIDTH
    lines = [
        bar,
        "INFOSECFOLLOW -- daily briefing on trending topics in security",
        digest["date"],
        bar,
        "",
        _fill(digest["headline"]),
        "",
        "EMERGING TRENDS",
        "-" * TEXT_WIDTH,
    ]
    lines += [_fill(trend, "* ", "  ") for trend in digest["emerging_trends"]]
    lines += ["", "TOPICS", "-" * TEXT_WIDTH]
    for n, topic in enumerate(digest["topics"], 1):
        lines += [
            "",
            _fill(topic["title"].upper()
                  + (f"  [{', '.join(topic['tags'])}]" if topic["tags"] else ""),
                  f"{n}. ", "   "),
            _fill(f"Last 24h: {topic['last_24h']}", "   "),
            _fill(topic["summary"], "   "),
        ]
        for src in topic["sources"]:
            if src["url"].startswith(("http://", "https://")):
                lines.append(f"   - {src['source']}: {src['url']}")
    lines += [
        "",
        bar,
        _fill(f"Generated {generated_at} from {len(feeds)} feeds. Summaries are "
              "AI-generated from the linked reporting; verify at the sources."),
        bar,
        "",
    ]
    return "\n".join(lines)


def render_archive_index():
    pages = sorted(
        (p.stem for p in (SITE_DIR / "archive").glob("*.html") if p.stem != "index"),
        reverse=True)
    items = "\n".join(
        f'<li><a href="{esc(d)}.html">{esc(d)}</a> (<a href="{esc(d)}.txt">txt</a>)</li>'
        for d in pages)
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>infosecfollow — archive</title>\n"
        f"<style>{PAGE_CSS}</style>\n</head>\n<body>\n<header>"
        '<h1><a href="../index.html" style="text-decoration:none">infosecfollow</a></h1>'
        "<p>archive of daily briefings</p></header>\n"
        f"<ul>\n{items}\n</ul>\n</body></html>\n")


def write_site(digest, feeds, items_count, window):
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    today = digest["date"]
    (SITE_DIR / "archive").mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "data").mkdir(parents=True, exist_ok=True)

    record = dict(digest)
    record["meta"] = {
        "generated_at": generated_at,
        "items_considered": items_count,
        "window_hours": window,
        "model": MODEL,
        "feeds": [f["name"] for f in feeds],
    }
    (SITE_DIR / "data" / f"{today}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    index_html = render_html(digest, feeds, generated_at,
                             "archive/index.html", "digest.txt", depth=0)
    archive_html = render_html(digest, feeds, generated_at,
                               "index.html", f"{today}.txt", depth=1)
    text = render_text(digest, feeds, generated_at)

    (SITE_DIR / "index.html").write_text(index_html, encoding="utf-8")
    (SITE_DIR / "digest.txt").write_text(text, encoding="utf-8")
    (SITE_DIR / "archive" / f"{today}.html").write_text(archive_html, encoding="utf-8")
    (SITE_DIR / "archive" / f"{today}.txt").write_text(text, encoding="utf-8")
    (SITE_DIR / "archive" / "index.html").write_text(render_archive_index(), encoding="utf-8")
    print(f"  wrote {SITE_DIR / 'index.html'}")


# --------------------------------------------------------------------------- main

def main():
    now = datetime.now(timezone.utc)
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    feeds = load_feeds()

    print(f"[1/3] fetching {len(feeds)} feeds")
    items, failures = fetch_all(feeds)
    healthy = len(feeds) - len(failures)
    if healthy < 2:
        sys.exit(f"only {healthy} feeds reachable; aborting")

    selected, window = select_window(items, now)
    if not selected:
        sys.exit("no recent items found in any feed; aborting")

    print(f"[2/3] summarizing {len(selected)} items via claude")
    digest = summarize(selected, window, today)
    digest["date"] = today  # never trust the model with the filename

    print("[3/3] writing site")
    write_site(digest, feeds, len(selected), window)
    print(f"done: {len(digest['topics'])} topics, {len(digest['emerging_trends'])} trends"
          + (f" (feed failures: {', '.join(failures)})" if failures else ""))


if __name__ == "__main__":
    main()
