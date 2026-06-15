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
EVENTS_WINDOW_HOURS = 120   # arts/events: weekly roundups + upcoming-event/ticket notices
EVENTS_MAX_ITEMS = 50
SPORTS_MEDIA_WINDOW_HOURS = 96  # team podcasts post ~weekly; beat writers daily
SPORTS_MEDIA_MAX_ITEMS = 30


def load_feeds():
    with open(ENGINE_DIR / "feeds.json", encoding="utf-8") as f:
        groups = json.load(f)
    for key in ("security", "pittsburgh", "bizpol", "events", "sports_media", "reading"):
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
        if not link:  # podcasts often omit <link>; fall back to a guid/enclosure URL
            guid = _child_text(elem, "guid")
            if guid.startswith(("http://", "https://")):
                link = guid
            else:
                enc = next((c for c in elem if _local(c.tag) == "enclosure"), None)
                if enc is not None and enc.get("url", "").startswith(("http://", "https://")):
                    link = enc.get("url")
        published = parse_date(_child_text(elem, "pubDate", "published", "updated", "date"))
        raw_summary = _child_text(elem, "description", "summary", "content", "encoded")
        if not raw_summary:  # YouTube Atom nests the text in media:group/media:description
            group = next((c for c in elem if _local(c.tag) == "group"), None)
            if group is not None:
                raw_summary = _child_text(group, "description")
        summary = clean_text(raw_summary, SUMMARY_CHARS)
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


def build_prompt(items, window, today, prior=None):
    corpus = corpus_of(items)
    prior_block = ""
    if prior:
        prior_block = f"""
PREVIOUSLY_REPORTED — topics this briefing already covered over the last week (most recent runs first), as a JSON array. Use it to tell new developments from old news:
{json.dumps(prior, ensure_ascii=False, indent=1)}
"""
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
      "latest_developments": "One sentence describing what is genuinely NEW about this topic today, relative to PREVIOUSLY_REPORTED.",
      "summary": "Two to four sentences of plain-text background and analysis: what it is, who is affected, what to do.",
      "tags": ["1-3 lowercase tags like ransomware, zero-day, apt, patch, breach, policy"],
      "sources": [{{"source": "outlet name", "title": "article title", "url": "exact url copied from the items below"}}]
    }}
  ]
}}

Rules:
- Aim for 5 to 8 topics, ordered most to least important. Merge near-duplicate coverage of the same story into one topic.
- Continuity with PREVIOUSLY_REPORTED (when present): "latest_developments" must describe only what is new today versus what was already reported. Include a topic ONLY if it has a genuinely new development; let a story that has stagnated with nothing new age out by dropping it entirely, even if that leaves fewer than 5 topics. Brand-new topics not in PREVIOUSLY_REPORTED are always welcome. If there is no prior coverage of a topic, "latest_developments" states the key current update.
- emerging_trends: 3 to 5 entries; "subject" is a one-or-two-word title-case label for the trend.
- Assign every topic an "area" naming its part of cybersecurity — e.g. Vulnerabilities and Exploits, Ransomware and Cybercrime, Nation-State Activity, AI Security, Data Breaches, Policy and Regulation. Use 2 to 5 distinct areas across the digest and repeat the exact same area string for topics that share it.
- Each topic cites 1 to 4 sources whose "url" values are copied EXACTLY from the items below. Never invent or modify a URL.
- Plain text only in every field: no markdown, no HTML, no bullet characters.
- Be concrete: name the malware, CVE IDs, vendors, and threat actors that appear in the items. Do not speculate beyond them.
- Skip vendor marketing and product-promo items unless they carry real news.

{STYLE_RULES}
{prior_block}
Items:
{json.dumps(corpus, ensure_ascii=False, indent=1)}
"""


def build_local_prompt(pgh_items, reading_items, biz_items, event_items, sports_items,
                       today, prior=None):
    prior_block = ""
    if prior:
        prior_block = f"""
PREVIOUSLY_REPORTED_LOCAL — items this briefing already covered over the last week (most recent runs first), grouped by section, as a JSON array. Use it to tell new developments from old news and to retire items that have nothing new:
{json.dumps(prior, ensure_ascii=False, indent=1)}
"""
    return f"""You are the editor of the Business and Politics, Pittsburgh, Events, Sports, and Reading sections of "infosecfollow", a daily plain-text briefing. Below are five JSON arrays: BUSINESS_POLITICS_ITEMS ({len(biz_items)} items from the Wall Street Journal, the Economist, and the Financial Times, last {BIZPOL_WINDOW_HOURS} hours), PITTSBURGH_ITEMS ({len(pgh_items)} local Pittsburgh news items, last {PGH_WINDOW_HOURS} hours), EVENTS_ITEMS ({len(event_items)} Pittsburgh arts, music, and things-to-do items, last {EVENTS_WINDOW_HOURS} hours), SPORTS_MEDIA_ITEMS ({len(sports_items)} items from Pittsburgh sports beat writers and team podcasts and video channels, last {SPORTS_MEDIA_WINDOW_HOURS} hours), and READING_ITEMS ({len(reading_items)} recent posts by the commentary writers Ed Zitron, Stratechery, and Cal Newport).

Respond with ONLY a JSON object (no markdown fences, no commentary) in exactly this shape:

{{
  "business_politics": [
    {{"title": "Short Title Naming the Story",
      "latest_developments": "One sentence on what is genuinely NEW about this story today, relative to PREVIOUSLY_REPORTED_LOCAL.",
      "summary": "One to three plain-text sentences of standalone background: what happened, who is affected, and why it matters.",
      "sources": [{{"source": "outlet", "title": "article title", "url": "exact url from BUSINESS_POLITICS_ITEMS"}}]}}
  ],
  "business": [same shape: Pittsburgh business/economy stories, cited from PITTSBURGH_ITEMS],
  "around_town": [same shape: civic news, development, transit, education, and other useful-to-know local items],
  "events": [same shape: arts, concerts, and things to attend; cited from EVENTS_ITEMS or PITTSBURGH_ITEMS],
  "around_teams": [same shape: what beat writers and team podcasts/channels are saying about the Steelers, Pirates, and Penguins; cited from SPORTS_MEDIA_ITEMS],
  "reading": [
    {{"author": "Ed Zitron|Stratechery|Cal Newport", "title": "post title", "url": "exact url", "summary": "One or two sentences on what the post argues."}}
  ]
}}

Rules:
- Every item in business_politics, business, around_town, events, and around_teams is an object with "title", "latest_developments", "summary", and "sources". Keep "title" a short title-case label; put the standalone detail in "summary".
- Continuity with PREVIOUSLY_REPORTED_LOCAL (when present): "latest_developments" states only what is new today versus what was already reported. Include an item ONLY if it is new or has a materially new development; let stories and events that have nothing new age out by dropping them — especially events whose date has already passed. Brand-new items are always welcome. When there is no prior coverage, "latest_developments" states the key current update.
- business_politics: 0 to 4 items, ONLY news of extraordinary significance — developments the chief risk officer of a globally systemically important bank must know: major central-bank decisions, sovereign-debt or currency crises, systemic market dislocations, failures or rescues of major institutions, landmark federal legislation or court rulings, wars or major escalations, and Pennsylvania or Pittsburgh developments of comparable weight. A typical day has zero or one item that clears this bar; return [] when nothing does. Cite urls EXACTLY from BUSINESS_POLITICS_ITEMS.
- business: 2-4 items. around_town: 3-5 items. Cite urls EXACTLY from PITTSBURGH_ITEMS.
- events: 0-6 items, only genuinely current or upcoming relative to {today}. Make each event stand alone: in "summary" include the event name, what it is, the date and day of week, the start time, the venue and its neighborhood or address, the ticket price or range, the on-sale date, and how or where to buy — whenever the source provides them. Never invent specifics the source does not state. Specifically surface tickets going on sale for future events, what is happening at the Pittsburgh Symphony, and notable concerts around town. Cite urls EXACTLY from EVENTS_ITEMS or PITTSBURGH_ITEMS.
- around_teams: 0-5 items covering the Pittsburgh Steelers, Pirates, and Penguins through their beat writers and team podcasts and video channels (for example "Footbahlin with Ben Roethlisberger" and "Not Just Football with Cam Heyward"). Summarize what was actually reported or said — roster moves, injuries, signings, draft and schedule talk, and notable opinions — so the item stands alone; name the show or writer in "summary" when the take comes from one. Do NOT restate box scores or final scores; the scoreboard already covers results. Cite urls EXACTLY from SPORTS_MEDIA_ITEMS.
- ABSOLUTE EXCLUSION: do not include any item about murder, shootings, stabbings, assault, fatal crashes, abuse, or other violent or graphic subject matter — skip those stories entirely no matter how prominent. Policy or court stories that are not centered on violence are fine.
- reading: pick the newest worthwhile post(s) per author from READING_ITEMS, up to 6 total; "url" copied EXACTLY. Skip housekeeping posts (podcast episode lists, link roundups) when a substantive essay is available.
- Plain text only in every field: no markdown, no HTML, no bullet characters. Never invent or modify a URL.
- Today is {today}.

{STYLE_RULES}
{prior_block}
BUSINESS_POLITICS_ITEMS:
{json.dumps(corpus_of(biz_items), ensure_ascii=False, indent=1)}

PITTSBURGH_ITEMS:
{json.dumps(corpus_of(pgh_items), ensure_ascii=False, indent=1)}

EVENTS_ITEMS:
{json.dumps(corpus_of(event_items), ensure_ascii=False, indent=1)}

SPORTS_MEDIA_ITEMS:
{json.dumps(corpus_of(sports_items), ensure_ascii=False, indent=1)}

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
            for key in ("title", "latest_developments", "summary"):
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


def validate_local(digest, pgh_urls, read_urls, biz_urls, event_urls, sports_urls,
                   have_pgh, have_reading):
    problems = []
    if not isinstance(digest, dict):
        raise ValueError("local digest must be an object")
    for key, allowed in (("business_politics", biz_urls), ("business", pgh_urls),
                         ("around_town", pgh_urls), ("events", event_urls | pgh_urls),
                         ("around_teams", sports_urls)):
        section = digest.get(key)
        if section is None:  # omitted/null key: treat as empty, not an error
            digest[key] = []
            continue
        if not isinstance(section, list):
            problems.append(f"{key} must be a list")
            digest[key] = []
            continue
        kept = []
        for item in section:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            latest = item.get("latest_developments")
            if not (isinstance(title, str) and title.strip()
                    and isinstance(latest, str) and latest.strip()):
                continue  # title + latest_developments are required, like a security topic
            sources = _valid_sources(item.get("sources"), allowed)
            if sources:  # drop items whose citations failed the allowlist
                summary = item.get("summary")
                kept.append({
                    "title": title.strip(),
                    "latest_developments": latest.strip(),
                    "summary": summary.strip() if isinstance(summary, str) else "",
                    "sources": sources,
                })
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


def recent_archive_digests(today_iso, days=7):
    """Compact topic history from the last `days` of data archives, newest first.

    Feeds the summarizer so it can separate new developments from old news and
    age out stagnated stories. Includes earlier runs of the same day, since the
    per-day data file still holds the prior run until this run overwrites it.
    """
    out = []
    for path, date in _archive_dates_within(today_iso, days):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        topics = [
            {"title": t.get("title", ""),
             "area": t.get("area", ""),
             "development": (t.get("latest_developments") or t.get("last_24h")
                             or t.get("summary", ""))}
            for t in data.get("topics", []) if isinstance(t, dict)
        ]
        if topics:
            out.append({"date": data.get("date", date), "topics": topics})
    return out


def summarize(cli, items, window, today, prior=None):
    allowed = {i["url"] for i in items}
    return ask_claude(cli, build_prompt(items, window, today, prior),
                      lambda digest: validate_digest(digest, allowed))


_LOCAL_SECTIONS = ("business_politics", "business", "around_town", "events", "around_teams")


def _archive_dates_within(today_iso, days):
    """Sorted (newest-first) data archive paths whose date stem is within `days`."""
    try:
        cutoff = (datetime.strptime(today_iso, "%Y-%m-%d")
                  - timedelta(days=days)).strftime("%Y-%m-%d")
    except ValueError:
        return []
    paths = []
    for path in sorted((SITE_DIR / "data").glob("*.json"), reverse=True):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", path.stem)
        if m and m.group(1) >= cutoff:
            paths.append((path, m.group(1)))
    return paths


def recent_archive_local(today_iso, days=7):
    """Compact per-section history of the local items from the last `days`.

    Feeds the local summarizer so it can separate new developments from old news
    and retire stale items and past events. Reads both the new object shape
    (title/latest_developments) and the legacy flat shape (text) of older
    archives.
    """
    out = []
    for path, date in _archive_dates_within(today_iso, days):
        try:
            local = json.loads(path.read_text(encoding="utf-8")).get("local") or {}
        except (ValueError, OSError):
            continue
        if not isinstance(local, dict):
            continue
        entry = {"date": date}
        for key in _LOCAL_SECTIONS:
            lines = []
            for item in (local.get(key) or []):
                if not isinstance(item, dict):
                    continue
                title = (item.get("title") or "").strip()
                latest = (item.get("latest_developments")
                          or item.get("text") or item.get("summary") or "").strip()
                lines.append(f"{title} — {latest}" if title and latest else (title or latest))
            entry[key] = [s for s in lines if s]
        if any(entry[k] for k in _LOCAL_SECTIONS):
            out.append(entry)
    return out


def summarize_local(cli, pgh_items, reading_items, biz_items, event_items, sports_items,
                    today, prior=None):
    pgh_urls = {i["url"] for i in pgh_items}
    read_urls = {i["url"] for i in reading_items}
    biz_urls = {i["url"] for i in biz_items}
    event_urls = {i["url"] for i in event_items}
    sports_urls = {i["url"] for i in sports_items}
    return ask_claude(
        cli, build_local_prompt(pgh_items, reading_items, biz_items, event_items,
                                sports_items, today, prior),
        lambda digest: validate_local(digest, pgh_urls, read_urls, biz_urls, event_urls,
                                      sports_urls, bool(pgh_items), bool(reading_items)))


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
  header p.runtime { margin: 0.35rem 0 0; opacity: 0.9; font-style: italic; }
  hr { border: 0; border-top: 1px solid currentColor; opacity: 0.25; margin: 1.5rem 0; }
  h2 { font-size: 1rem; text-transform: uppercase; letter-spacing: 0.08em;
       margin: 2rem 0 0.75rem; scroll-margin-top: 0.5rem; }
  h3 { font-size: 1rem; margin: 1.75rem 0 0.25rem; }
  ul { padding-left: 1.25rem; margin: 0.5rem 0; }
  li { margin: 0.4rem 0; }
  p { margin: 0.5rem 0; }
  a { color: inherit; }
  .updated { font-style: italic; }
  details.more summary { cursor: pointer; opacity: 0.7; font-size: 0.85rem; }
  details.more[open] summary { margin-bottom: 0.25rem; }
  .tags { font-size: 0.8rem; opacity: 0.7; }
  .sources { font-size: 0.85rem; margin-top: 0.4rem; }
  .sources a { overflow-wrap: anywhere; }
  .headline { font-size: 1.05rem; font-weight: bold; margin-top: 1rem; }
  nav { font-size: 0.85rem; margin-top: 0.25rem; }
  pre { margin: 0.5rem 0; overflow-x: auto; line-height: 1.5;
        font-family: inherit; font-size: inherit; }
  .team { font-weight: bold; margin: 1rem 0 0.1rem; }
  .gameline { margin: 0.35rem 0 0; }
  .lbl { opacity: 0.6; }
  .sub { opacity: 0.65; margin: 0.1rem 0 0 1.4em; }
  a.game { color: #9a6f00; font-weight: bold; text-underline-offset: 2px;
           overflow-wrap: anywhere; }
  ul.headlines { margin: 0.25rem 0 0; }
  @media (prefers-color-scheme: dark) { a.game { color: #ffd24a; } }
  .index { font-size: 0.85rem; opacity: 0.85; margin: 0.75rem 0; }
  .index a { margin-right: 0.25rem; }
  .up { color: #157f3b; } .down { color: #c0392b; } .flat { opacity: 0.7; }
  @media (prefers-color-scheme: dark) {
    .up { color: #5dd48f; } .down { color: #ff8a80; }
  }
  h3.area { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em;
            opacity: 0.75; margin: 2rem 0 0; }
  h4 { font-size: 1rem; margin: 1.5rem 0 0.25rem; }
"""


def _display_date(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%A, %B %-d, %Y")
    except ValueError:
        return iso


def _ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _friendly_run_time(dt):
    """e.g. 'Monday, June 15th 2026 @ 9:00 AM EST'."""
    return dt.strftime(f"%A, %B {_ordinal(dt.day)} %Y @ %-I:%M %p %Z")


def _markets_inner(markets):
    width_label = max(len(r["label"]) for r in markets)
    width_value = max(len(r["value"]) for r in markets)
    rows = []
    for r in markets:
        cls = "up" if r["arrow"] == "▲" else ("down" if r["arrow"] == "▼" else "flat")
        rows.append(f"{esc(r['label'].ljust(width_label))}  "
                    f"{esc(r['value'].rjust(width_value))}  "
                    f'<span class="{cls}">{esc(r["arrow"])} {esc(r["pct"])}</span>')
    return ['<p class="tags">weekly average, change vs prior week</p>',
            '<pre class="markets">' + "\n".join(rows) + "</pre>"]


def _local_items_html(items):
    """Render local items like security topics: title, latest-developments line,
    a collapsible summary, and sources."""
    out = []
    for item in items:
        out.append(f'<h4>{esc(item["title"])}</h4>')
        out.append('<p class="updated">Latest developments: '
                   f'{esc(item["latest_developments"])}</p>')
        if item.get("summary"):
            out.append(f'<details class="more"><summary>read more</summary>'
                       f'<p>{esc(item["summary"])}</p></details>')
        links = " &middot; ".join(
            f'<a href="{safe_url(s["url"])}">{esc(s["source"] or s["title"] or "source")}</a>'
            for s in item["sources"])
        out.append(f'<p class="sources">Sources: {links}</p>')
    return out


def _clean_sports(blocks):
    """Strip control chars and cap lengths on third-party ESPN sports strings."""
    for b in blocks:
        b["team"] = sanitize(b.get("team", ""))[:80]
        b["record"] = sanitize(b.get("record", ""))[:20]
        for g in b.get("games", []):
            g["date"] = sanitize(g.get("date", ""))[:40]
            g["result"] = sanitize(g.get("result", ""))[:160]
            g["recap"] = sanitize(g.get("recap", ""))[:300]
        if b.get("next"):
            b["next"]["matchup"] = sanitize(b["next"].get("matchup", ""))[:80]
            b["next"]["when"] = sanitize(b["next"].get("when", ""))[:60]
        b["headlines"] = [sanitize(h)[:200] for h in b.get("headlines", [])]
    return blocks


def _trends_inner(digest):
    out = ["<ul>"]
    out += [f"<li><strong>{esc(t['subject'])}:</strong> {esc(t['text'])}</li>"
            for t in digest["emerging_trends"]]
    out.append("</ul>")
    return out


def _security_inner(digest):
    out, current_area = [], None
    for n, topic in enumerate(digest["topics"], 1):
        if topic["area"] != current_area:
            current_area = topic["area"]
            out.append(f'<h3 class="area">{esc(current_area)}</h3>')
        out.append(f"<h4>{n}. {esc(topic['title'])}</h4>")
        if topic["tags"]:
            out.append(f'<p class="tags">[{esc(", ".join(topic["tags"]))}]</p>')
        out.append(f'<p class="updated">Latest developments: {esc(topic["latest_developments"])}</p>')
        out.append(f'<details class="more"><summary>read more</summary>'
                   f'<p>{esc(topic["summary"])}</p></details>')
        if topic["sources"]:
            links = " &middot; ".join(
                f'<a href="{safe_url(s["url"])}">{esc(s["source"] or s["title"] or "source")}</a>'
                for s in topic["sources"])
            out.append(f'<p class="sources">Sources: {links}</p>')
    return out


def _pittsburgh_inner(local, weather):
    parts = []
    if weather:
        parts.append("<h3>Weather</h3>")
        parts += [f"<p>{esc(line)}</p>" for line in weather]
    for key, label in (("business", "Business"), ("around_town", "Around Town"),
                       ("events", "Events")):
        if local and local.get(key):
            parts.append(f"<h3>{label}</h3>")
            parts += _local_items_html(local[key])
    return parts


def _game_link(text, url):
    """Matchup text as a yellow link to its plaintextsports page (URL hidden)."""
    if url and url.startswith(("http://", "https://")):
        return f'<a class="game" href="{esc(url)}">{esc(text)}</a>'
    return esc(text)


def _sports_inner(blocks):
    if not blocks:
        return []
    out = []
    for b in blocks:
        head = esc(b["team"]) + (f" ({esc(b['record'])})" if b["record"] else "")
        out.append(f'<p class="team">{head}</p>')
        for g in b["games"]:
            out.append('<p class="gameline">'
                       f'<span class="lbl">{esc(g["date"])} &middot;</span> '
                       f'{_game_link(g["result"], g["url"])}</p>')
            if g["recap"]:
                out.append(f'<p class="sub">{esc(g["recap"])}</p>')
        nxt = b.get("next")
        if nxt:
            out.append('<p class="gameline"><span class="lbl">Up Next &middot;</span> '
                       f'{_game_link(nxt["matchup"], nxt["url"])} '
                       f'<span class="lbl">&middot; {esc(nxt["when"])}</span></p>')
        if b["headlines"]:
            out.append('<ul class="headlines">')
            out += [f"<li>{esc(h)}</li>" for h in b["headlines"]]
            out.append("</ul>")
    return out


def _sports_section(sports, local):
    """ESPN scoreboard plus the model-summarized 'Around the Teams' items."""
    out = _sports_inner(sports)
    around = local.get("around_teams") if local else None
    if around:
        out.append("<h3>Around the Teams</h3>")
        out += _local_items_html(around)
    return out


def _reading_inner(local):
    if not local or not local.get("reading"):
        return []
    parts = ["<ul>"]
    for item in local["reading"]:
        parts.append(f'<li><strong>{esc(item["author"])}</strong> &mdash; '
                     f'<a href="{safe_url(item["url"])}">{esc(item["title"])}</a>. '
                     f'{esc(item["summary"])}</li>')
    parts.append("</ul>")
    return parts


def render_html(digest, local, markets, weather, sports, feeds,
                generated_at, archive_href, text_href, run_time=None, depth=0):
    prefix = "../" * depth
    biz = local.get("business_politics") if local else None
    # Ordered most-frequently-updated first; the weekly markets average sits
    # last. Only non-empty sections render and appear in the jump index.
    sections = [
        ("trends", "Emerging Trends", _trends_inner(digest)),
        ("security", "Security", _security_inner(digest)),
        ("business", "Business and Politics", _local_items_html(biz) if biz else []),
        ("pittsburgh", "Pittsburgh", _pittsburgh_inner(local, weather)),
        ("sports", "Sports", _sports_section(sports, local)),
        ("reading", "Reading", _reading_inner(local)),
        ("markets", "Markets", _markets_inner(markets) if markets else []),
    ]
    present = [(anchor, title, body) for anchor, title, body in sections if body]
    index = " &middot; ".join(f'<a href="#{a}">{esc(t)}</a>' for a, t, _ in present)

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
        *([f'<p class="runtime">{esc(run_time)}</p>'] if run_time else []),
        f"<nav>{esc(_display_date(digest['date']))} &middot; "
        f'<a href="{archive_href}">archive</a> &middot; '
        f'<a href="{text_href}">plain text</a></nav>',
        "</header>",
        f'<p class="headline">{esc(digest["headline"])}</p>',
        f'<nav class="index">Jump to: {index}</nav>',
        "<hr>",
    ]
    for anchor, title, body in present:
        parts.append(f'<h2 id="{anchor}">{esc(title)}</h2>')
        parts += body
    parts += [
        "<hr>",
        "<footer>",
        f"<p>Generated {esc(generated_at)}. Sources: {len(feeds['security'])} security feeds; "
        f"{len(feeds['pittsburgh'])} Pittsburgh feeds; {len(feeds['events'])} Pittsburgh "
        f"arts and events feeds; {len(feeds['sports_media'])} Pittsburgh sports beat and "
        "podcast feeds; the Wall Street Journal, the "
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


def _text_local_item(item):
    """Plain-text lines for one local item: title, developments, summary, sources."""
    out = [_fill(item["title"], "* ", "  "),
           _fill(f"Latest developments: {item['latest_developments']}", "  ")]
    if item.get("summary"):
        out.append(_fill(item["summary"], "  "))
    for src in item["sources"]:
        if src["url"].startswith(("http://", "https://")):
            out.append(f"  - {src['source']}: {src['url']}")
    return out


def _text_local_items(lines, label, items):
    if not items:
        return
    lines += ["", f"{label}:"]
    for item in items:
        lines += _text_local_item(item)


def render_text(digest, local, markets, weather, sports, feeds, generated_at):
    bar = "=" * TEXT_WIDTH
    sub = "-" * TEXT_WIDTH
    biz = local.get("business_politics") if local else None
    has_pgh = bool(weather) or bool(local and any(
        local.get(k) for k in ("business", "around_town", "events")))

    around_teams = local.get("around_teams") if local else None
    contents = ["Emerging Trends", "Security"]
    if biz:
        contents.append("Business and Politics")
    if has_pgh:
        contents.append("Pittsburgh")
    if sports or around_teams:
        contents.append("Sports")
    if local and local.get("reading"):
        contents.append("Reading")
    if markets:
        contents.append("Markets")

    lines = [
        bar,
        "INFOSECFOLLOW -- security, markets, business, pittsburgh",
        _display_date(digest["date"]),
        bar,
        "",
        _fill(digest["headline"]),
        "",
        _fill("CONTENTS: " + " | ".join(contents)),
    ]

    # Most frequently updated first.
    lines += ["", "EMERGING TRENDS", sub]
    lines += [_fill(f"{t['subject']}: {t['text']}", "* ", "  ")
              for t in digest["emerging_trends"]]

    lines += ["", "SECURITY", sub]
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
            _fill(f"Latest developments: {topic['latest_developments']}", "   "),
            _fill(topic["summary"], "   "),
        ]
        for src in topic["sources"]:
            if src["url"].startswith(("http://", "https://")):
                lines.append(f"   - {src['source']}: {src['url']}")

    if biz:
        lines += ["", "BUSINESS AND POLITICS", sub]
        for item in biz:
            lines += _text_local_item(item)

    if has_pgh:
        lines += ["", "PITTSBURGH", sub]
        if weather:
            lines += ["", "Weather:"] + [_fill(w, "  ", "    ") for w in weather]
        if local:
            _text_local_items(lines, "Business", local.get("business", []))
            _text_local_items(lines, "Around town", local.get("around_town", []))
            _text_local_items(lines, "Events", local.get("events", []))

    if sports or around_teams:
        lines += ["", "SPORTS", sub]
        for b in (sports or []):
            head = f"{b['team']} ({b['record']})" if b["record"] else b["team"]
            lines += ["", head]
            for g in b["games"]:
                lines.append(_fill(f"{g['date']} · {g['result']}", "  ", "    "))
                if g["recap"]:
                    lines.append(_fill(g["recap"], "    "))
                if g["url"].startswith(("http://", "https://")):
                    lines.append(f"    {g['url']}")
            nxt = b.get("next")
            if nxt:
                lines.append(_fill(f"Up Next · {nxt['matchup']} · {nxt['when']}",
                                   "  ", "    "))
                if nxt["url"].startswith(("http://", "https://")):
                    lines.append(f"    {nxt['url']}")
            if b["headlines"]:
                lines.append("  Headlines:")
                for h in b["headlines"]:
                    lines.append(_fill(h, "    · ", "      "))
        _text_local_items(lines, "Around the Teams", around_teams or [])

    if local and local.get("reading"):
        lines += ["", "READING", sub]
        for item in local["reading"]:
            lines += [
                "",
                _fill(f"{item['author']} -- {item['title']}", "* ", "  "),
                _fill(item["summary"], "  "),
            ]
            if item["url"].startswith(("http://", "https://")):
                lines.append(f"  {item['url']}")

    # Weekly average last.
    if markets:
        lines += ["", "MARKETS (weekly average, change vs prior week)", sub]
        lines += market_data.as_lines(markets)

    lines += [
        "",
        bar,
        _fill(f"Generated {generated_at}. Sources: {len(feeds['security'])} security "
              f"feeds; {len(feeds['pittsburgh'])} Pittsburgh feeds; {len(feeds['events'])} "
              f"Pittsburgh arts and events feeds; {len(feeds['sports_media'])} Pittsburgh "
              "sports beat and podcast feeds; the Wall Street "
              "Journal, the Economist, and the Financial Times; and "
              f"{', '.join(f['name'] for f in feeds['reading'])}. Markets from Yahoo "
              "Finance, weather from the NWS, scores from ESPN. Summaries are "
              "AI-generated from the linked reporting; verify at the sources."),
        bar,
        "",
    ]
    return "\n".join(lines)


def render_archive_index():
    # Stems are either "YYYY-MM-DD" (legacy, one per day) or "YYYY-MM-DD-HHMM"
    # (one per run). Group every run under its day, newest day and run first.
    runs = {}  # date -> list of (stem, time_label), newest run first
    for path in (SITE_DIR / "archive").glob("*.html"):
        if path.stem == "index":
            continue
        m = re.match(r"(\d{4}-\d{2}-\d{2})(?:-(\d{2})(\d{2}))?$", path.stem)
        if not m:
            continue
        label = f"{m.group(2)}:{m.group(3)}" if m.group(2) else "briefing"
        runs.setdefault(m.group(1), []).append((path.stem, label))
    sections = []
    for date in sorted(runs, reverse=True):
        rows = "\n".join(
            f'<li><a href="{esc(stem)}.html">{esc(label)}</a> '
            f'(<a href="{esc(stem)}.txt">txt</a>)</li>'
            for stem, label in sorted(runs[date], reverse=True))
        sections.append(f"<h3>{esc(date)}</h3>\n<ul>\n{rows}\n</ul>")
    items = "\n".join(sections)
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>infosecfollow — archive</title>\n"
        f"<style>{PAGE_CSS}</style>\n</head>\n<body>\n<header>"
        '<h1><a href="../index.html" style="text-decoration:none">infosecfollow</a></h1>'
        "<p>archive of briefings (multiple runs per day)</p></header>\n"
        f"{items}\n</body></html>\n")


def write_site(digest, local, markets, weather, sports, feeds, items_count, window):
    now_local = datetime.now().astimezone()
    generated_at = now_local.strftime("%Y-%m-%d %H:%M %Z")
    run_time = _friendly_run_time(now_local)
    stamp = now_local.strftime("%Y-%m-%d-%H%M")  # one archive page per run
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
                             generated_at, "archive/index.html", "digest.txt",
                             run_time=run_time, depth=0)
    archive_html = render_html(digest, local, markets, weather, sports, feeds,
                               generated_at, "index.html", f"{stamp}.txt",
                               run_time=run_time, depth=1)
    text = render_text(digest, local, markets, weather, sports, feeds, generated_at)

    (SITE_DIR / "index.html").write_text(index_html, encoding="utf-8")
    (SITE_DIR / "digest.txt").write_text(text, encoding="utf-8")
    (SITE_DIR / "archive" / f"{stamp}.html").write_text(archive_html, encoding="utf-8")
    (SITE_DIR / "archive" / f"{stamp}.txt").write_text(text, encoding="utf-8")
    (SITE_DIR / "archive" / "index.html").write_text(render_archive_index(), encoding="utf-8")
    print(f"  wrote {SITE_DIR / 'index.html'}")


# --------------------------------------------------------------------------- main

def main():
    now = datetime.now(timezone.utc)
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    feeds = load_feeds()

    print(f"[1/4] fetching feeds "
          f"(security {len(feeds['security'])}, pittsburgh {len(feeds['pittsburgh'])}, "
          f"bizpol {len(feeds['bizpol'])}, events {len(feeds['events'])}, "
          f"sports_media {len(feeds['sports_media'])}, reading {len(feeds['reading'])})")
    sec_items, sec_failures = fetch_all(feeds["security"])
    pgh_items, pgh_failures = fetch_all(feeds["pittsburgh"])
    biz_items, biz_failures = fetch_all(feeds["bizpol"])
    event_items, event_failures = fetch_all(feeds["events"])
    sports_items, sports_failures = fetch_all(feeds["sports_media"])
    read_items, read_failures = fetch_all(feeds["reading"])
    failures = (sec_failures + pgh_failures + biz_failures
                + event_failures + sports_failures + read_failures)
    if len(feeds["security"]) - len(sec_failures) < 2:
        sys.exit(f"only {len(feeds['security']) - len(sec_failures)} security feeds "
                 "reachable; aborting")

    selected, window = select_window(sec_items, now)
    if not selected:
        sys.exit("no recent security items found; aborting")
    pgh_selected = recent_items(pgh_items, now, PGH_WINDOW_HOURS, PGH_MAX_ITEMS)
    read_selected = recent_items(read_items, now, READING_WINDOW_HOURS, READING_MAX_ITEMS)
    biz_selected = recent_items(biz_items, now, BIZPOL_WINDOW_HOURS, BIZPOL_MAX_ITEMS)
    event_selected = recent_items(event_items, now, EVENTS_WINDOW_HOURS, EVENTS_MAX_ITEMS)
    sports_selected = recent_items(sports_items, now, SPORTS_MEDIA_WINDOW_HOURS,
                                   SPORTS_MEDIA_MAX_ITEMS)

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
    sports = _clean_sports(attempt("sports", pgh_data.sports_blocks) or [])

    cli = find_claude_cli()
    print(f"[3/4] summarizing via claude ({MODEL}, using {cli})\n"
          f"  security: {len(selected)} items ({window}h); pittsburgh: "
          f"{len(pgh_selected)}; bizpol: {len(biz_selected)}; "
          f"events: {len(event_selected)}; sports_media: {len(sports_selected)}; "
          f"reading: {len(read_selected)}")
    prior = recent_archive_digests(today)
    prior_local = recent_archive_local(today)
    if prior:
        print(f"  prior coverage: {sum(len(d['topics']) for d in prior)} topics "
              f"across {len(prior)} archived runs (last week)")
    with ThreadPoolExecutor(max_workers=2) as pool:
        digest_future = pool.submit(summarize, cli, selected, window, today, prior)
        local_future = (pool.submit(summarize_local, cli, pgh_selected, read_selected,
                                    biz_selected, event_selected, sports_selected,
                                    today, prior_local)
                        if pgh_selected or read_selected or biz_selected
                        or event_selected or sports_selected else None)
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
          f"local items, {len(local.get('around_teams', [])) if local else 0} around-teams, "
          f"{len(local.get('reading', [])) if local else 0} reading items, "
          f"{len(markets)} market rows"
          + (f" (feed failures: {', '.join(failures)})" if failures else ""))


if __name__ == "__main__":
    main()
