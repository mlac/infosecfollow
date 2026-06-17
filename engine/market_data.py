"""Weekly-average market data via Yahoo Finance's public chart API.

Each row is the mean of the last 5 daily closes vs the mean of the 5 before
that (week over week), with a trend arrow. Stdlib only, no API key.
"""

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from statistics import mean

import safefetch

TIMEOUT = 20
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


def _closes(symbol):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(symbol)}?range=1mo&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (infosecfollow)"})
    with safefetch.safe_open(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read(4_000_000).decode("utf-8", "replace"))
    result = data["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    closes = result["indicators"]["quote"][0]["close"]
    pairs = [(t, c) for t, c in zip(timestamps, closes) if c is not None]
    # Yahoo appends a bar for the current, still-trading session (its "close"
    # is the live price); drop it so the average uses completed sessions only.
    today = datetime.now(timezone.utc).date()
    if pairs and datetime.fromtimestamp(pairs[-1][0], tz=timezone.utc).date() >= today:
        pairs = pairs[:-1]
    return [c for _, c in pairs]


def weekly_rows():
    """Return [{label, value, pct, arrow}] — rows that fail are skipped."""
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
            print(f"  markets: {label} unavailable: {str(exc)[:120]}")
    return rows


def as_lines(rows):
    """Fixed-width text lines, shared by the HTML <pre> and digest.txt."""
    if not rows:
        return []
    width_label = max(len(r["label"]) for r in rows)
    width_value = max(len(r["value"]) for r in rows)
    return [
        f"{r['label']:<{width_label}}  {r['value']:>{width_value}}  {r['arrow']} {r['pct']}"
        for r in rows
    ]


if __name__ == "__main__":
    print("\n".join(as_lines(weekly_rows())))
