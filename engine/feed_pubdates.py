#!/usr/bin/env python3
"""Profile the publish-time distribution of every infosecfollow feed.

Read-only analysis. Reuses the engine's hardened fetch + parse path
(USER_AGENT + safefetch.safe_open via generate.http_get, generate.parse_feed),
so feeds don't 403 and stays SSRF-safe.

Each run fetches every feed in feeds.json (all groups), records each dated item
once (deduped by URL) into logs/feed_pubdates.jsonl, appends a run record to
logs/feed_pubdates_runs.jsonl, then reports the accumulated distribution.

Idempotent and safe to run repeatedly: append-and-dedupe. Run hourly for a week
and the time series fills in. Stdlib only.

    python3 engine/feed_pubdates.py
"""

import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import generate

PROJECT_DIR = generate.PROJECT_DIR
LOGS_DIR = PROJECT_DIR / "logs"
PUBDATES_PATH = LOGS_DIR / "feed_pubdates.jsonl"
RUNS_PATH = LOGS_DIR / "feed_pubdates_runs.jsonl"
ET = ZoneInfo("America/New_York")
GROUPS = ("security", "pittsburgh", "bizpol", "events", "sports_media", "reading")


# --------------------------------------------------------------------------- fetch

def fetch_group_items(groups):
    """Fetch every feed in every group concurrently, tagging each item with its
    group. Tolerates per-feed failure: logs it and keeps going. Returns
    (items, attempted, failed)."""
    jobs = []  # (group, feed)
    for group in GROUPS:
        for feed in groups.get(group, []):
            jobs.append((group, feed))

    items, failed = [], []

    def fetch_one(group, feed):
        # generate.http_get sets USER_AGENT and goes through safefetch.safe_open;
        # generate.parse_feed handles RSS/RDF/Atom.
        parsed = list(generate.parse_feed(feed["name"], generate.http_get(feed["url"])))
        return group, feed, parsed

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_one, g, f): (g, f) for g, f in jobs}
        for future in as_completed(futures):
            group, feed = futures[future]
            try:
                group, feed, parsed = future.result()
                for it in parsed:
                    it["group"] = group
                items.extend(parsed)
                print(f"  ok   [{group}] {feed['name']}: {len(parsed)} items")
            except Exception as exc:
                failed.append(feed["name"])
                print(f"  FAIL [{group}] {feed['name']}: "
                      f"{generate.sanitize(exc)[:300]}")
    return items, len(jobs), failed


# --------------------------------------------------------------------------- log I/O

def load_seen_urls():
    """URLs already recorded, so repeated runs accumulate instead of double-count."""
    seen = set()
    if not PUBDATES_PATH.exists():
        return seen
    with PUBDATES_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            url = rec.get("url")
            if url:
                seen.add(url)
    return seen


def append_new_items(items, seen, now):
    """Append each dated, not-yet-seen item as one JSON line. Returns count added.
    Dedupe is in-run as well as cross-run, so two feeds carrying the same URL in
    one fetch only record it once."""
    LOGS_DIR.mkdir(exist_ok=True)
    added = 0
    now_iso = now.isoformat()
    with PUBDATES_PATH.open("a", encoding="utf-8") as f:
        for it in items:
            url = (it.get("url") or "").strip()
            pub = it.get("published")  # generate.parse_feed gives an aware UTC datetime or None
            if not url or pub is None:
                continue  # skip items with no parseable date
            if url in seen:
                continue
            seen.add(url)
            pub_et = pub.astimezone(ET)
            rec = {
                "url": url,
                "feed": it.get("source", ""),
                "group": it.get("group", ""),
                "published_utc": pub.isoformat(),
                "published_et_hour": pub_et.hour,
                "published_weekday": pub_et.strftime("%A"),
                "first_seen_utc": now_iso,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            added += 1
    return added


def append_run_record(now, attempted, failed, added):
    LOGS_DIR.mkdir(exist_ok=True)
    rec = {
        "timestamp": now.isoformat(),
        "feeds_attempted": attempted,
        "feeds_failed": len(failed),
        "failed_names": failed,
        "new_items_added": added,
    }
    with RUNS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load_all_records():
    records = []
    if not PUBDATES_PATH.exists():
        return records
    with PUBDATES_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                continue
    return records


# --------------------------------------------------------------------------- report

WEEKEND = {"Saturday", "Sunday"}


def _bar(count, total, width=40):
    if total <= 0:
        return ""
    return "#" * max(1, round(width * count / total)) if count else ""


def _hour_histogram(label, recs):
    counts = [0] * 24
    for r in recs:
        h = r.get("published_et_hour")
        if isinstance(h, int) and 0 <= h <= 23:
            counts[h] += 1
    total = sum(counts)
    print(f"\n  {label} (n={total})")
    if not total:
        print("    (no items)")
        return
    peak = max(counts)
    for h in range(24):
        c = counts[h]
        print(f"    {h:02d}  {_bar(c, peak):<40} {c}")


def _four_hour_blocks(recs):
    blocks = [0] * 6  # 00-04, 04-08, 08-12, 12-16, 16-20, 20-24
    for r in recs:
        h = r.get("published_et_hour")
        if isinstance(h, int) and 0 <= h <= 23:
            blocks[h // 4] += 1
    return blocks


def _block_table(by_group):
    labels = ["00-04", "04-08", "08-12", "12-16", "16-20", "20-24"]
    print("\n  Share of items per 4-hour ET block, per group")
    header = "    {:<14}".format("group") + "".join(f"{l:>8}" for l in labels) + f"{'n':>8}"
    print(header)
    for group in GROUPS + ("ALL",):
        recs = by_group.get(group, [])
        blocks = _four_hour_blocks(recs)
        n = sum(blocks)
        if not n:
            row = "    {:<14}".format(group) + "".join(f"{'-':>8}" for _ in labels) + f"{0:>8}"
        else:
            row = "    {:<14}".format(group) + "".join(
                f"{100*b/n:>7.0f}%" for b in blocks) + f"{n:>8}"
        print(row)


def _weekday_weekend(recs):
    wd = sum(1 for r in recs if r.get("published_weekday") not in WEEKEND
             and r.get("published_weekday"))
    we = sum(1 for r in recs if r.get("published_weekday") in WEEKEND)
    return wd, we


def _freshness_lag(by_group):
    """Median + p90 of (first_seen_utc - published_utc) in hours, per group."""
    print("\n  Freshness lag — first_seen minus published (how stale items are "
          "when first caught)")
    print("    {:<14}{:>12}{:>12}{:>8}".format("group", "median(h)", "p90(h)", "n"))
    for group in GROUPS + ("ALL",):
        lags = []
        for r in by_group.get(group, []):
            try:
                pub = datetime.fromisoformat(r["published_utc"])
                seen = datetime.fromisoformat(r["first_seen_utc"])
            except (KeyError, ValueError):
                continue
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if seen.tzinfo is None:
                seen = seen.replace(tzinfo=timezone.utc)
            lags.append((seen - pub).total_seconds() / 3600.0)
        if not lags:
            print("    {:<14}{:>12}{:>12}{:>8}".format(group, "-", "-", 0))
            continue
        lags.sort()
        median = statistics.median(lags)
        # p90 by nearest-rank
        p90 = lags[min(len(lags) - 1, max(0, round(0.9 * len(lags)) - 1))]
        print("    {:<14}{:>12.1f}{:>12.1f}{:>8}".format(group, median, p90, len(lags)))


def report(records):
    print("\n" + "=" * 64)
    print("FEED PUBLISH-TIME DISTRIBUTION REPORT")
    print("=" * 64)
    if not records:
        print("\nNo records yet. Run again after feeds have been fetched.")
        return

    pubs = []
    for r in records:
        try:
            dt = datetime.fromisoformat(r["published_utc"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            pubs.append(dt)
        except (KeyError, ValueError):
            continue
    print(f"\n  Total items: {len(records)}")
    if pubs:
        lo, hi = min(pubs), max(pubs)
        span_days = (hi - lo).total_seconds() / 86400.0
        print(f"  Published date span: {lo.date()} -> {hi.date()} "
              f"({span_days:.1f} days)")

    by_group = {}
    for r in records:
        by_group.setdefault(r.get("group", ""), []).append(r)
    by_group["ALL"] = records

    print("\n" + "-" * 64)
    print("HISTOGRAM OF PUBLISHED HOUR (ET, 0-23)")
    print("-" * 64)
    _hour_histogram("ALL", records)
    for group in GROUPS:
        if by_group.get(group):
            _hour_histogram(group, by_group[group])

    print("\n" + "-" * 64)
    print("4-HOUR ET BLOCKS")
    print("-" * 64)
    _block_table(by_group)

    print("\n" + "-" * 64)
    print("WEEKDAY vs WEEKEND (by ET publish day)")
    print("-" * 64)
    print("\n    {:<14}{:>10}{:>10}{:>10}".format("group", "weekday", "weekend", "wknd%"))
    for group in GROUPS + ("ALL",):
        wd, we = _weekday_weekend(by_group.get(group, []))
        tot = wd + we
        pct = f"{100*we/tot:.0f}%" if tot else "-"
        print("    {:<14}{:>10}{:>10}{:>10}".format(group, wd, we, pct))

    print("\n" + "-" * 64)
    print("FRESHNESS LAG")
    print("-" * 64)
    _freshness_lag(by_group)
    print()


# --------------------------------------------------------------------------- main

def main():
    now = datetime.now(timezone.utc)
    groups = generate.load_feeds()
    print("Fetching feeds...")
    items, attempted, failed = fetch_group_items(groups)

    seen = load_seen_urls()
    added = append_new_items(items, seen, now)
    append_run_record(now, attempted, failed, added)
    print(f"\nRun: {attempted} feeds attempted, {len(failed)} failed, "
          f"{added} new items added.")

    report(load_all_records())


if __name__ == "__main__":
    main()
