"""Weekly-average market data via Yahoo Finance's public chart API.

Each row is the mean of the last 5 daily closes vs the mean of the 5 before
that (week over week), with a trend arrow. Stdlib only, no API key.
"""

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from statistics import mean

import safefetch

TIMEOUT = 20            # per socket operation
DEADLINE = 45           # whole response, wall clock
MAX_BYTES = 4_000_000
SYMBOLS = [
    # label, yahoo symbol, decimal places
    ("S&P 500", "^GSPC", 2),
    ("Dow", "^DJI", 2),
    ("Nasdaq", "^IXIC", 2),
    ("WTI crude", "CL=F", 2),
    ("EUR/USD", "EURUSD=X", 4),
    ("GBP/USD", "GBPUSD=X", 4),
    ("USD/JPY", "JPY=X", 2),
]


def _session_open(result, last_ts, now_ts):
    """True if the bar stamped `last_ts` belongs to a session that is still
    trading, so its "close" is a live price rather than a settled one.

    Yahoo stamps daily bars at the session open and reports the current
    session's regular-hours end in meta.currentTradingPeriod. When that is
    known, the bar is final once the session has ended; otherwise fall back to
    the conservative date rule (any bar dated today is treated as live).
    """
    today = datetime.fromtimestamp(now_ts, tz=timezone.utc).date()
    bar_day = datetime.fromtimestamp(last_ts, tz=timezone.utc).date()
    if bar_day < today:
        return False
    meta = result.get("meta") or {}
    end = ((meta.get("currentTradingPeriod") or {}).get("regular") or {}).get("end")
    if isinstance(end, (int, float)) and end >= last_ts:
        return now_ts < end
    return True


def _closes(symbol, now_ts=None):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(symbol)}?range=1mo&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (infosecfollow)"})
    with safefetch.safe_open(req, timeout=TIMEOUT) as resp:
        raw = safefetch.read_bounded(resp, MAX_BYTES, DEADLINE)
    data = json.loads(raw.decode("utf-8", "replace"))
    result = data["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    closes = result["indicators"]["quote"][0]["close"]
    pairs = [(t, c) for t, c in zip(timestamps, closes) if c is not None]
    # Drop the bar for a session that is still trading (its "close" is the
    # live price) so the average uses completed sessions only.
    now_ts = time.time() if now_ts is None else now_ts
    if pairs and _session_open(result, pairs[-1][0], now_ts):
        pairs = pairs[:-1]
    return [c for _, c in pairs]


def weekly_rows(errors=None):
    """Return [{label, value, pct, arrow}] — rows that fail are skipped.

    Failures are printed and, when `errors` is a list, appended to it as
    "label: reason" strings so the run can report them.
    """
    rows = []
    for label, symbol, digits in SYMBOLS:
        try:
            closes = _closes(symbol)
            if len(closes) < 10:
                raise ValueError(f"only {len(closes)} closes available")
            current, previous = mean(closes[-5:]), mean(closes[-10:-5])
            pct = (current - previous) / previous * 100
            arrow = "=" if abs(pct) < 0.05 else ("▲" if pct > 0 else "▼")
            rows.append({
                "label": label,
                "value": f"{current:,.{digits}f}",
                "pct": f"{pct:+.1f}%",
                "arrow": arrow,
            })
        except Exception as exc:
            reason = str(exc)[:120]
            print(f"  markets: {label} unavailable: {reason}")
            if errors is not None:
                errors.append(f"{label}: {reason}")
    return rows


def format_rows(rows):
    """Column-aligned pieces for each row: (label, value, arrow, pct), padded so
    the labels and values line up. Shared by the HTML <pre> and digest.txt so
    the two renditions cannot drift."""
    if not rows:
        return []
    width_label = max(len(r["label"]) for r in rows)
    width_value = max(len(r["value"]) for r in rows)
    return [(r["label"].ljust(width_label), r["value"].rjust(width_value),
             r["arrow"], r["pct"]) for r in rows]


def as_lines(rows):
    """Fixed-width text lines, shared by the HTML <pre> and digest.txt."""
    return [f"{label}  {value}  {arrow} {pct}"
            for label, value, arrow, pct in format_rows(rows)]


if __name__ == "__main__":
    print("\n".join(as_lines(weekly_rows())))
