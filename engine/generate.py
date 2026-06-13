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

import market_data
import pittsburgh as pgh_data

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

PGH_WINDOW_HOURS = 48       # Pittsburgh items lookback
PGH_MAX_ITEMS = 60
READING_WINDOW_HOURS = 14 * 24  # commentary authors post ~weekly
READING_MAX_ITEMS = 12
BIZPOL_WINDOW_HOURS = 36    # WSJ/Economist/FT lookback
BIZPOL_MAX_ITEMS = 60


def load_feeds():
    with open(ENGINE_DIR / "feeds.json", encoding="utf-8") as f:
        groups = json.load(f)
    for key in ("security", "pittsburgh", "bizpol", "reading"):
        if key not in groups:
            raise ValueError(f"feeds.json missing group '{key}'")
    return groups


STYLE_RULES = """Style rules for every word you write:
- Voice: write like John McPhee — factual, dense, and conversational, never flowery and never academic. Active voice only; eliminate every passive construction. No contrastive negation, antithesis, or "X, not Y" constructions. Compress hard: deliver the most information in the fewest words, suitable for a Fortune 500 CEO. Every item stands alone; the reader never needs the source for pertinent details.
- Capitalization: capitalize only the formal names of specific entities, people, and places; lowercase common nouns, general concepts, and statistical metrics. Capitalize professional titles only immediately before a name ("Chief Executive Jane Roe" but "the chief executive said"). Capitalize compass points only when they name recognized regions (the Midwest, Western Pennsylvania); lowercase directional uses (the storm moved east).
- Titles and headings (topic titles, trend subjects, area names): use title case — capitalize the first word, the last word, and all principal words; lowercase articles, coordinating conjunctions, and prepositions of fewer than four letters.
- Mechanics: American spelling (color, realize, traveling). Use the Oxford comma in series of three or more. Put periods and commas inside quotation marks; put colons and semicolons outside. Use unspaced em dashes for parenthetical interruptions—like this. One space after terminal punctuation. Write dates as Month Day, Year (June 12, 2026). Corporate entities and organizations take singular verbs.
"""


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
    # tolerate a UTF-8 BOM or blank lines before the XML declaration (TribLive)
    root = ElementTree.fromstring(raw.lstrip(b"\xef\xbb\xbf\r\n\t "))
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


def recent_items(items, now, hours, cap):
    """Items from the last `hours`, future-dated dropped, deduped, newest first."""
    horizon = now + timedelta(hours=FUTURE_SLACK_HOURS)  # drop bogus future dates
    cutoff = now - timedelta(hours=hours)
    selected = [i for i in items if i["published"] and cutoff <= i["published"] <= horizon]
    seen, deduped = set(), []
    for item in sorted(selected, key=lambda i: i["published"], reverse=True):
        key = re.sub(r"\W+", "", item["title"].lower())
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped[:cap]


def select_window(items, now):
    """Keep items from the last 24h (48h if the day is thin), dedupe, cap."""
    window = WINDOW_HOURS
    selected = recent_items(items, now, window, MAX_ITEMS)
    if len(selected) < MIN_ITEMS:
        window = FALLBACK_WINDOW_HOURS
        selected = recent_items(items, now, window, MAX_ITEMS)
    return selected, window


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


def corpus_of(items):
    return [
        {
            "source": i["source"],
            "title": i["title"],
            "url": i["url"],
            "published": i["published"].strftime("%Y-%m-%d %H:%M UTC"),
            "summary": i["summary"],
        }
        for i in items
    ]


def build_prompt(items, window, today):
    corpus = corpus_of(items)
    return f"""You are the editor of "infosecfollow", a daily plain-text briefing on information security. Below are {len(corpus)} news items published in the last {window} hours by major security outlets, vendors, and government sources, as a JSON array.

Cluster them into the day's trending topics and respond with ONLY a JSON object (no markdown fences, no commentary) in exactly this shape:

{{
  "date": "{today}",
  "headline": "One sentence capturing the most important security story or theme of the day.",
  "emerging_trends": [
    {{"subject": "One or Two Words", "text": "A single sentence naming a trend visible across multiple items and why it matters."}}
  ],
  "topics": [
    {{
      "title": "Short Topic Name (a Campaign, Vulnerability, Incident, or Theme)",
      "area": "The Area of Cybersecurity This Topic Belongs To",
      "last_24h": "One sentence describing the relevant updates on this topic in the last 24 hours.",
      "summary": "Two to four sentences of plain-text background and analysis: what it is, who is affected, what to do.",
      "tags": ["1-3 lowercase tags like ransomware, zero-day, apt, patch, breach, policy"],
      "sources": [{{"source": "outlet name", "title": "article title", "url": "exact url copied from the items below"}}]
    }}
  ]
}}

Rules:
- 5 to 8 topics, ordered most to least important. Merge near-duplicate coverage of the same story into one topic.
- emerging_trends: 3 to 5 entries; "subject" is a one-or-two-word title-case label for the trend.
- Assign every topic an "area" naming its part of cybersecurity — e.g. Vulnerabilities and Exploits, Ransomware and Cybercrime, Nation-State Activity, AI Security, Data Breaches, Policy and Regulation. Use 2 to 5 distinct areas across the digest and repeat the exact same area string for topics that share it.
- Each topic cites 1 to 4 sources whose "url" values are copied EXACTLY from the items below. Never invent or modify a URL.
- Plain text only in every field: no markdown, no HTML, no bullet characters.
- Be concrete: name the malware, CVE IDs, vendors, and threat actors that appear in the items. Do not speculate beyond them.
- Skip vendor marketing and product-promo items unless they carry real news.

{STYLE_RULES}

Items:
{json.dumps(corpus, ensure_ascii=False, indent=1)}
"""


def build_local_prompt(pgh_items, reading_items, biz_items, today):
    return f"""You are the editor of the Business and Politics, Pittsburgh, and Reading sections of "infosecfollow", a daily plain-text briefing. Below are three JSON arrays: BUSINESS_POLITICS_ITEMS ({len(biz_items)} items from the Wall Street Journal, the Economist, and the Financial Times, last {BIZPOL_WINDOW_HOURS} hours), PITTSBURGH_ITEMS ({len(pgh_items)} local Pittsburgh news items, last {PGH_WINDOW_HOURS} hours), and READING_ITEMS ({len(reading_items)} recent posts by the commentary writers Ed Zitron, Stratechery, and Cal Newport).

Respond with ONLY a JSON object (no markdown fences, no commentary) in exactly this shape:

{{
  "business_politics": [
    {{"text": "One or two plain-text sentences on the development and why it matters.",
      "sources": [{{"source": "outlet", "title": "article title", "url": "exact url from BUSINESS_POLITICS_ITEMS"}}]}}
  ],
  "business": [same shape: Pittsburgh business/economy stories, cited from PITTSBURGH_ITEMS],
  "around_town": [same shape: civic news, development, transit, education, and other useful-to-know local items],
  "events": [same shape: things happening today or in the next few days that a reader could attend],
  "reading": [
    {{"author": "Ed Zitron|Stratechery|Cal Newport", "title": "post title", "url": "exact url", "summary": "One or two sentences on what the post argues."}}
  ]
}}

Rules:
- business_politics: 0 to 4 items, ONLY news of extraordinary significance — developments the chief risk officer of a globally systemically important bank must know: major central-bank decisions, sovereign-debt or currency crises, systemic market dislocations, failures or rescues of major institutions, landmark federal legislation or court rulings, wars or major escalations, and Pennsylvania or Pittsburgh developments of comparable weight. A typical day has zero or one item that clears this bar; return [] when nothing does. Cite urls EXACTLY from BUSINESS_POLITICS_ITEMS.
- business: 2-4 items. around_town: 3-5 items. events: 0-5 items (only genuinely current or upcoming; include day/venue when the item mentions them). Cite urls EXACTLY from PITTSBURGH_ITEMS.
- ABSOLUTE EXCLUSION: do not include any item about murder, shootings, stabbings, assault, fatal crashes, abuse, or other violent or graphic subject matter — skip those stories entirely no matter how prominent. Policy or court stories that are not centered on violence are fine.
- reading: pick the newest worthwhile post(s) per author from READING_ITEMS, up to 6 total; "url" copied EXACTLY. Skip housekeeping posts (podcast episode lists, link roundups) when a substantive essay is available.
- Plain text only in every field: no markdown, no HTML, no bullet characters. Never invent or modify a URL.
- Today is {today}.

{STYLE_RULES}

BUSINESS_POLITICS_ITEMS:
{json.dumps(corpus_of(biz_items), ensure_ascii=False, indent=1)}

PITTSBURGH_ITEMS:
{json.dumps(corpus_of(pgh_items), ensure_ascii=False, indent=1)}

READING_ITEMS:
{json.dumps(corpus_of(reading_items), ensure_ascii=False, indent=1)}
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

    def _trend_ok(t):
        return (isinstance(t, dict)
                and all(isinstance(t.get(k), str) and t.get(k).strip()
                        for k in ("subject", "text")))

    if not isinstance(trends, list) or not trends or not all(_trend_ok(t) for t in trends):
        problems.append("emerging_trends must be a non-empty list of "
                        "{subject, text} objects")
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
            area = topic.get("area")
            topic["area"] = area.strip() if isinstance(area, str) and area.strip() else "Other"
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
    # group topics by area, preserving the order in which areas first appear
    areas = []
    for topic in topics:
        if topic["area"] not in areas:
            areas.append(topic["area"])
    digest["topics"] = [t for a in areas for t in topics if t["area"] == a]
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


def _valid_sources(raw, allowed_urls):
    sources = []
    for src in (raw if isinstance(raw, list) else []):
        url = src.get("url", "") if isinstance(src, dict) else ""
        if url in allowed_urls:
            sources.append({
                "source": str(src.get("source", "")),
                "title": str(src.get("title", "")),
                "url": url,
            })
    return sources


def validate_local(digest, pgh_urls, read_urls, biz_urls, have_pgh, have_reading):
    problems = []
    if not isinstance(digest, dict):
        raise ValueError("local digest must be an object")
    for key, allowed in (("business_politics", biz_urls), ("business", pgh_urls),
                         ("around_town", pgh_urls), ("events", pgh_urls)):
        section = digest.get(key)
        if not isinstance(section, list):
            problems.append(f"{key} must be a list")
            digest[key] = []
            continue
        kept = []
        for item in section:
            if not isinstance(item, dict) or not isinstance(item.get("text"), str) \
                    or not item.get("text").strip():
                continue
            sources = _valid_sources(item.get("sources"), allowed)
            if sources:  # drop items whose citations failed the allowlist
                kept.append({"text": item["text"].strip(), "sources": sources})
        digest[key] = kept
    if have_pgh and not any(digest[k] for k in ("business", "around_town", "events")):
        problems.append("business, around_town, and events are all empty; cite urls "
                        "exactly as given in PITTSBURGH_ITEMS")

    reading = digest.get("reading")
    kept = []
    for item in (reading if isinstance(reading, list) else []):
        if isinstance(item, dict) and item.get("url") in read_urls \
                and all(isinstance(item.get(k), str) and item.get(k).strip()
                        for k in ("author", "title", "summary")):
            kept.append({k: item[k].strip() for k in ("author", "title", "url", "summary")})
    digest["reading"] = kept
    if have_reading and not kept:
        problems.append("reading is empty; pick posts from READING_ITEMS with exact urls")

    if problems:
        raise ValueError("; ".join(problems))
    return digest


def ask_claude(cli, prompt, validate):
    """Run the locked-down headless call, parse + validate JSON, retry once."""
    last_error = None
    for attempt in (1, 2):
        try:
            output = run_claude(cli, prompt)
            return validate(extract_json(output))
        except (ValueError, TypeError, AttributeError, KeyError,
                subprocess.TimeoutExpired) as exc:
            last_error = exc
            print(f"  attempt {attempt} failed: {type(exc).__name__}: {sanitize(exc)[:300]}")
            prompt += ("\n\nIMPORTANT: your previous reply was rejected "
                       f"({sanitize(exc)[:300]}). Respond again with ONLY a single valid "
                       "JSON object in the required shape, nothing else.")
    raise RuntimeError(f"model never produced a valid digest: {last_error}")


def summarize(cli, items, window, today):
    allowed = {i["url"] for i in items}
    return ask_claude(cli, build_prompt(items, window, today),
                      lambda digest: validate_digest(digest, allowed))


def summarize_local(cli, pgh_items, reading_items, biz_items, today):
    pgh_urls = {i["url"] for i in pgh_items}
    read_urls = {i["url"] for i in reading_items}
    biz_urls = {i["url"] for i in biz_items}
    return ask_claude(cli, build_local_prompt(pgh_items, reading_items, biz_items, today),
                      lambda digest: validate_local(digest, pgh_urls, read_urls, biz_urls,
                                                    bool(pgh_items), bool(reading_items)))


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
  pre { margin: 0.5rem 0; overflow-x: auto; line-height: 1.5;
        font-family: inherit; font-size: inherit; }
  pre.scores { white-space: pre-wrap; overflow-wrap: anywhere; }
  .topbar { display: flex; flex-wrap: wrap; gap: 0 2.5rem; align-items: center; }
  .topbar .headline { flex: 1; min-width: 16rem; }
  .up { color: #157f3b; } .down { color: #c0392b; } .flat { opacity: 0.7; }
  @media (prefers-color-scheme: dark) {
    .up { color: #5dd48f; } .down { color: #ff8a80; }
  }
  h3.area { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em;
            opacity: 0.75; margin: 2rem 0 0; }
  h4 { font-size: 1rem; margin: 1.5rem 0 0.25rem; }
"""


def _markets_html(markets):
    if not markets:
        return []
    width_label = max(len(r["label"]) for r in markets)
    width_value = max(len(r["value"]) for r in markets)
    rows = []
    for r in markets:
        cls = "up" if r["arrow"] == "▲" else ("down" if r["arrow"] == "▼" else "flat")
        rows.append(f"{esc(r['label'].ljust(width_label))}  "
                    f"{esc(r['value'].rjust(width_value))}  "
                    f'<span class="{cls}">{esc(r["arrow"])} {esc(r["pct"])}</span>')
    return ['<div class="markets-block">',
            "<h2>Markets</h2>",
            '<p class="tags">weekly average, change vs prior week</p>',
            '<pre class="markets">' + "\n".join(rows) + "</pre>",
            "</div>"]


def _local_items_html(items):
    out = ["<ul>"]
    for item in items:
        links = " &middot; ".join(
            f'<a href="{safe_url(s["url"])}">{esc(s["source"] or s["title"] or "source")}</a>'
            for s in item["sources"])
        out.append(f'<li>{esc(item["text"])} <span class="sources">({links})</span></li>')
    out.append("</ul>")
    return out


_URL_RE = re.compile(r"https://[^\s<]+")


def _linkify(escaped_line):
    return _URL_RE.sub(lambda m: f'<a href="{m.group(0)}">{m.group(0)}</a>', escaped_line)


def _pittsburgh_html(local, weather, sports):
    parts = []
    if weather:
        parts.append("<h3>Weather</h3>")
        parts += [f"<p>{esc(line)}</p>" for line in weather]
    if sports:
        parts.append("<h3>Sports</h3>")
        parts.append('<pre class="scores">'
                     + "\n".join(_linkify(esc(l)) for l in sports) + "</pre>")
    for key, label in (("business", "Business"), ("around_town", "Around town"),
                       ("events", "Events")):
        if local and local.get(key):
            parts.append(f"<h3>{label}</h3>")
            parts += _local_items_html(local[key])
    return (["<h2>Pittsburgh</h2>"] + parts) if parts else []


def _reading_html(local):
    if not local or not local.get("reading"):
        return []
    parts = ["<h2>Reading</h2>", "<ul>"]
    for item in local["reading"]:
        parts.append(f'<li><strong>{esc(item["author"])}</strong> &mdash; '
                     f'<a href="{safe_url(item["url"])}">{esc(item["title"])}</a>. '
                     f'{esc(item["summary"])}</li>')
    parts.append("</ul>")
    return parts


def render_html(digest, local, markets, weather, sports, feeds,
                generated_at, archive_href, text_href, depth=0):
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
        "<p>daily plain-text briefing: security, markets, business, and pittsburgh</p>",
        f"<nav>{esc(digest['date'])} &middot; <a href=\"{archive_href}\">archive</a> &middot; "
        f"<a href=\"{text_href}\">plain text</a></nav>",
        "</header>",
        '<div class="topbar">',
    ]
    parts += _markets_html(markets)
    parts += [
        f'<p class="headline">{esc(digest["headline"])}</p>',
        "</div>",
        "<hr>",
        "<h2>Emerging Trends</h2>",
        "<ul>",
    ]
    parts += [f"<li><strong>{esc(trend['subject'])}:</strong> {esc(trend['text'])}</li>"
              for trend in digest["emerging_trends"]]
    parts.append("</ul>")
    parts.append("<h2>Topics</h2>")
    current_area = None
    for n, topic in enumerate(digest["topics"], 1):
        if topic["area"] != current_area:
            current_area = topic["area"]
            parts.append(f'<h3 class="area">{esc(current_area)}</h3>')
        parts.append(f"<h4>{n}. {esc(topic['title'])}</h4>")
        if topic["tags"]:
            parts.append(f'<p class="tags">[{esc(", ".join(topic["tags"]))}]</p>')
        parts.append(f'<p class="updated">Last 24h: {esc(topic["last_24h"])}</p>')
        parts.append(f"<p>{esc(topic['summary'])}</p>")
        if topic["sources"]:
            links = " &middot; ".join(
                f'<a href="{safe_url(s["url"])}">{esc(s["source"] or s["title"] or "source")}</a>'
                for s in topic["sources"])
            parts.append(f'<p class="sources">Sources: {links}</p>')
    if local and local.get("business_politics"):
        parts.append("<h2>Business and Politics</h2>")
        parts += _local_items_html(local["business_politics"])
    parts += _pittsburgh_html(local, weather, sports)
    parts += _reading_html(local)
    parts += [
        "<hr>",
        "<footer>",
        f"<p>Generated {esc(generated_at)}. Sources: {len(feeds['security'])} security feeds; "
        f"{len(feeds['pittsburgh'])} Pittsburgh feeds; the Wall Street Journal, the "
        "Economist, and the Financial Times; and "
        f"{esc(', '.join(f['name'] for f in feeds['reading']))}. Market data from Yahoo "
        "Finance (weekly averages), weather from the National Weather Service, scores "
        "from ESPN.</p>",
        "<p>Summaries are AI-generated from the linked reporting; verify details at the sources.</p>",
        "</footer>",
        "</body></html>",
    ]
    return "\n".join(parts)


def _fill(text, initial="", subsequent=None):
    return textwrap.fill(text, width=TEXT_WIDTH, initial_indent=initial,
                         subsequent_indent=initial if subsequent is None else subsequent,
                         break_long_words=False, break_on_hyphens=False)


def _text_local_items(lines, label, items):
    if not items:
        return
    lines += ["", f"{label}:"]
    for item in items:
        lines.append(_fill(item["text"], "* ", "  "))
        for src in item["sources"]:
            if src["url"].startswith(("http://", "https://")):
                lines.append(f"  - {src['source']}: {src['url']}")


def render_text(digest, local, markets, weather, sports, feeds, generated_at):
    bar = "=" * TEXT_WIDTH
    lines = [
        bar,
        "INFOSECFOLLOW -- security, markets, business, pittsburgh",
        digest["date"],
        bar,
    ]
    if markets:
        lines += ["", "MARKETS (weekly average, change vs prior week)",
                  "-" * TEXT_WIDTH]
        lines += market_data.as_lines(markets)
    lines += [
        "",
        _fill(digest["headline"]),
        "",
        "EMERGING TRENDS",
        "-" * TEXT_WIDTH,
    ]
    lines += [_fill(f"{t['subject']}: {t['text']}", "* ", "  ")
              for t in digest["emerging_trends"]]
    lines += ["", "TOPICS", "-" * TEXT_WIDTH]
    current_area = None
    for n, topic in enumerate(digest["topics"], 1):
        if topic["area"] != current_area:
            current_area = topic["area"]
            lines += ["", f":: {current_area.upper()}"]
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

    if local and local.get("business_politics"):
        lines += ["", "BUSINESS AND POLITICS", "-" * TEXT_WIDTH]
        for item in local["business_politics"]:
            lines.append(_fill(item["text"], "* ", "  "))
            for src in item["sources"]:
                if src["url"].startswith(("http://", "https://")):
                    lines.append(f"  - {src['source']}: {src['url']}")

    if weather or sports or (local and any(local.get(k) for k in
                                           ("business", "around_town", "events"))):
        lines += ["", "PITTSBURGH", "-" * TEXT_WIDTH]
        if weather:
            lines += ["", "Weather:"] + [_fill(w, "  ", "    ") for w in weather]
        if sports:
            lines += ["", "Sports:"] + [f"  {s}" for s in sports]
        if local:
            _text_local_items(lines, "Business", local.get("business", []))
            _text_local_items(lines, "Around town", local.get("around_town", []))
            _text_local_items(lines, "Events", local.get("events", []))

    if local and local.get("reading"):
        lines += ["", "READING", "-" * TEXT_WIDTH]
        for item in local["reading"]:
            lines += [
                "",
                _fill(f"{item['author']} -- {item['title']}", "* ", "  "),
                _fill(item["summary"], "  "),
            ]
            if item["url"].startswith(("http://", "https://")):
                lines.append(f"  {item['url']}")

    lines += [
        "",
        bar,
        _fill(f"Generated {generated_at}. Sources: {len(feeds['security'])} security "
              f"feeds; {len(feeds['pittsburgh'])} Pittsburgh feeds; the Wall Street "
              "Journal, the Economist, and the Financial Times; and "
              f"{', '.join(f['name'] for f in feeds['reading'])}. Markets from Yahoo "
              "Finance, weather from the NWS, scores from ESPN. Summaries are "
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


def write_site(digest, local, markets, weather, sports, feeds, items_count, window):
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    today = digest["date"]
    (SITE_DIR / "archive").mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "data").mkdir(parents=True, exist_ok=True)

    record = dict(digest)
    record["markets"] = markets
    record["weather"] = weather
    record["sports"] = sports
    record["local"] = local
    record["meta"] = {
        "generated_at": generated_at,
        "items_considered": items_count,
        "window_hours": window,
        "model": MODEL,
        "feeds": {group: [f["name"] for f in entries]
                  for group, entries in feeds.items()},
    }
    (SITE_DIR / "data" / f"{today}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    index_html = render_html(digest, local, markets, weather, sports, feeds,
                             generated_at, "archive/index.html", "digest.txt", depth=0)
    archive_html = render_html(digest, local, markets, weather, sports, feeds,
                               generated_at, "index.html", f"{today}.txt", depth=1)
    text = render_text(digest, local, markets, weather, sports, feeds, generated_at)

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

    print(f"[1/4] fetching feeds "
          f"(security {len(feeds['security'])}, pittsburgh {len(feeds['pittsburgh'])}, "
          f"bizpol {len(feeds['bizpol'])}, reading {len(feeds['reading'])})")
    sec_items, sec_failures = fetch_all(feeds["security"])
    pgh_items, pgh_failures = fetch_all(feeds["pittsburgh"])
    biz_items, biz_failures = fetch_all(feeds["bizpol"])
    read_items, read_failures = fetch_all(feeds["reading"])
    failures = sec_failures + pgh_failures + biz_failures + read_failures
    if len(feeds["security"]) - len(sec_failures) < 2:
        sys.exit(f"only {len(feeds['security']) - len(sec_failures)} security feeds "
                 "reachable; aborting")

    selected, window = select_window(sec_items, now)
    if not selected:
        sys.exit("no recent security items found; aborting")
    pgh_selected = recent_items(pgh_items, now, PGH_WINDOW_HOURS, PGH_MAX_ITEMS)
    read_selected = recent_items(read_items, now, READING_WINDOW_HOURS, READING_MAX_ITEMS)
    biz_selected = recent_items(biz_items, now, BIZPOL_WINDOW_HOURS, BIZPOL_MAX_ITEMS)

    print("[2/4] markets, weather, sports")
    def attempt(label, fn):
        try:
            return fn()
        except Exception as exc:
            print(f"  {label} unavailable: {sanitize(exc)[:200]}")
            return []
    markets = attempt("markets", market_data.weekly_rows)
    # NWS/ESPN strings are third-party text: strip control chars, cap length
    weather = [sanitize(w)[:200] for w in attempt("weather", pgh_data.weather_lines)]
    sports = [sanitize(s)[:200] for s in attempt("sports", pgh_data.sports_lines)]

    cli = find_claude_cli()
    print(f"[3/4] summarizing via claude ({MODEL}, using {cli})\n"
          f"  security: {len(selected)} items ({window}h); pittsburgh: "
          f"{len(pgh_selected)}; bizpol: {len(biz_selected)}; "
          f"reading: {len(read_selected)}")
    with ThreadPoolExecutor(max_workers=2) as pool:
        digest_future = pool.submit(summarize, cli, selected, window, today)
        local_future = (pool.submit(summarize_local, cli, pgh_selected,
                                    read_selected, biz_selected, today)
                        if pgh_selected or read_selected or biz_selected else None)
        try:
            digest = digest_future.result()
        except Exception:
            if local_future is not None and not local_future.cancel():
                print("  security digest failed; waiting for the in-flight "
                      "pittsburgh/reading call to finish before aborting")
            raise
        local = None
        if local_future is not None:
            try:
                local = local_future.result()
            except Exception as exc:
                print(f"  pittsburgh/reading sections unavailable: {sanitize(exc)[:200]}")
    digest["date"] = today  # never trust the model with the filename

    print("[4/4] writing site")
    write_site(digest, local, markets, weather, sports, feeds, len(selected), window)
    print(f"done: {len(digest['topics'])} security topics, "
          f"{len(digest['emerging_trends'])} trends, "
          f"{sum(len(local.get(k, [])) for k in ('business', 'around_town', 'events')) if local else 0} "
          f"local items, {len(local.get('reading', [])) if local else 0} reading items, "
          f"{len(markets)} market rows"
          + (f" (feed failures: {', '.join(failures)})" if failures else ""))


if __name__ == "__main__":
    main()
