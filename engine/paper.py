"""paper.txt: the briefing as one story per screen for the M5Stack PaperS3.

Each story is a block of plain ASCII lines, and stories are separated by a
form feed (\\f) on its own line:

    KICKER                       line 1, small type (section and area)
    Headline in Title Case       line 2, bold display type

    Lede paragraph.              every later non-blank line is one paragraph
    *Why it matters:* text.      a leading *Label:* renders in bold
    Sources: Outlet, Outlet

The reader sketch (devices/papers3/) lays a story out with the same fonts,
geometry, and word-wrap rule as layout() below, so the generator can prove that
every story fits on one 540x960 screen before it publishes. When a story runs
long, fit_story() drops its trailing detail paragraphs first, then the sources
line, then shortens the longest paragraph with an ellipsis.

Change the geometry here and in the sketch together.
"""

import re
import unicodedata

from paper_fonts import FONTS

# --- geometry shared with devices/papers3/PaperS3_InfosecFollow.ino ---------
SCREEN_W, SCREEN_H = 540, 960
MARGIN_X = 18
HEADER_H = 48
FOOTER_H = 40
TOP_PAD = 6
BOTTOM_PAD = 4
KICKER_FONT, KICKER_GAP = "DejaVu18", 8
HEAD_FONT, HEAD_GAP = "FreeSansBold18pt7b", 8
BODY_FONT, BODY_LEADING, PARA_GAP = "DejaVu24", 4, 10
MAX_HEAD_LINES = 3

TEXT_W = SCREEN_W - 2 * MARGIN_X
CONTENT_TOP = HEADER_H + TOP_PAD
CONTENT_BOTTOM = SCREEN_H - FOOTER_H - BOTTOM_PAD

_LABEL_RE = re.compile(r"^\*([^*]{1,40}:)\*\s*(.*)$")

_ASCII_MAP = {
    "—": "--", "–": "-", "‒": "-", "‐": "-", "‑": "-",
    "‘": "'", "’": "'", "‚": "'", "“": '"', "”": '"',
    "…": "...", "•": "*", "·": "-", "→": "->", "←": "<-",
    " ": " ", " ": " ", " ": " ", "×": "x", "−": "-",
    "°": " deg", "€": "EUR ", "£": "GBP ", "¥": "JPY ",
}


def to_ascii(text):
    """Printable ASCII only: the device fonts cover 0x20-0x7E."""
    text = str(text or "")
    for src, dst in _ASCII_MAP.items():
        text = text.replace(src, dst)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if 0x20 <= ord(ch) <= 0x7E)
    return re.sub(r"\s+", " ", text).strip()


# --- measurement: a port of LovyanGFX LGFXBase::text_width() ----------------

def line_height(font):
    return FONTS[font][0]


def text_width(text, font):
    glyphs = FONTS[font][1]
    left = right = 0
    for ch in text:
        code = ord(ch)
        adv, width, xoff = glyphs[code - 0x20] if 0x20 <= code <= 0x7E else glyphs[0]
        if left == 0 and right == 0 and xoff < 0:
            left = right = -xoff
        right = left + max(adv, width + xoff)
        left += adv
    return right


def split_label(paragraph):
    """('Why it matters:', 'rest') for a *Label:* paragraph, else ('', text)."""
    m = _LABEL_RE.match(paragraph)
    if not m:
        return "", paragraph
    return m.group(1), m.group(2)


def wrap(text, font, bold_chars=0, max_w=TEXT_W):
    """Greedy word wrap, identical to the sketch's wrapParagraph(). The first
    `bold_chars` characters render in fake bold (drawn twice, 1 px apart), so a
    line that holds them measures 1 px wider."""
    lines, line = [], ""
    for word in text.split(" "):
        if not word:
            continue
        candidate = word if not line else line + " " + word
        extra = 1 if (bold_chars and not lines) else 0
        if text_width(candidate, font) + extra <= max_w:
            line = candidate
            continue
        if line:
            lines.append(line)
            line = ""
        while text_width(word, font) > max_w and len(word) > 1:
            cut = len(word) - 1
            while cut > 1 and text_width(word[:cut], font) > max_w:
                cut -= 1
            lines.append(word[:cut])
            word = word[cut:]
        line = word
    if line:
        lines.append(line)
    return lines


def layout(story):
    """Bottom y (pixels) of a laid-out story; it fits when <= CONTENT_BOTTOM."""
    y = CONTENT_TOP + line_height(KICKER_FONT) + KICKER_GAP
    y += len(wrap(story["headline"], HEAD_FONT)) * line_height(HEAD_FONT) + HEAD_GAP
    pitch = line_height(BODY_FONT) + BODY_LEADING
    for n, para in enumerate(story["paras"]):
        if n:
            y += PARA_GAP
        label, rest = split_label(para)
        shown = f"{label} {rest}".strip() if label else para
        y += len(wrap(shown, BODY_FONT, len(label))) * pitch
    return y


def fits(story):
    return layout(story) <= CONTENT_BOTTOM


def _truncate_words(text, keep_words):
    words = text.split(" ")
    if len(words) <= keep_words:
        return text
    return " ".join(words[:keep_words]).rstrip(",;:.") + "..."


def fit_story(story):
    """Trim a story until it fits one screen (see module docstring)."""
    story = {"kicker": story["kicker"], "headline": story["headline"],
             "paras": list(story["paras"]), "droppable": list(story.get("droppable", []))}
    # The kicker is a single line; the headline gets at most MAX_HEAD_LINES.
    while story["kicker"] and text_width(story["kicker"], KICKER_FONT) > TEXT_W:
        story["kicker"] = story["kicker"][:-1].rstrip()
    while len(wrap(story["headline"], HEAD_FONT)) > MAX_HEAD_LINES:
        words = story["headline"].split(" ")
        story["headline"] = _truncate_words(story["headline"].rstrip("."), len(words) - 1)
    # Drop optional paragraphs, last first (details, then the sources line).
    while not fits(story) and story["droppable"]:
        idx = story["droppable"].pop()
        story["paras"].pop(idx)
        story["droppable"] = [i if i < idx else i - 1 for i in story["droppable"]]
    # Then shorten the longest paragraph a word at a time.
    while not fits(story) and story["paras"]:
        longest = max(range(len(story["paras"])), key=lambda i: len(story["paras"][i]))
        words = story["paras"][longest].split(" ")
        if len(words) <= 3:
            story["paras"].pop(longest)
            continue
        story["paras"][longest] = _truncate_words(story["paras"][longest], len(words) - 2)
    return {"kicker": story["kicker"], "headline": story["headline"], "paras": story["paras"]}


# --- building stories from the day's record ---------------------------------

def _label(label, text):
    text = to_ascii(text)
    return f"*{to_ascii(label).rstrip(':')}:* {text}" if text else ""


def _sources_line(sources):
    names = []
    for s in sources or []:
        if isinstance(s, dict):
            name = to_ascii(s.get("source") or s.get("title") or "")
            if name and name not in names:
                names.append(name)
    return ("Sources: " + ", ".join(names)) if names else ""


def news_story(kicker, item):
    """A security topic or local news item in Smart Brevity order: lede, why it
    matters, up to three labeled details, sources. Older records without the
    Smart Brevity fields fall back to their summary paragraph."""
    paras, droppable = [], []
    lede = to_ascii(item.get("latest_developments"))
    if lede:
        paras.append(lede)
    why = _label("Why it matters", item.get("why_it_matters"))
    if why:
        paras.append(why)
    details = [d for d in (item.get("details") or []) if isinstance(d, dict)]
    for d in details[:3]:
        line = _label(d.get("label", ""), d.get("text", ""))
        if line:
            droppable.append(len(paras))
            paras.append(line)
    if not why and not details and item.get("summary"):
        droppable.append(len(paras))
        paras.append(to_ascii(item["summary"]))
    src = _sources_line(item.get("sources"))
    if src:
        droppable.append(len(paras))
        paras.append(src)
    return {"kicker": to_ascii(kicker).upper(), "headline": to_ascii(item.get("title")),
            "paras": paras, "droppable": droppable}


def cover_story(record, edition_label, counts):
    paras = [to_ascii(record.get("headline"))]
    paras.append(_label("Edition", edition_label))
    inside = ", ".join(f"{n} {name}" for name, n in counts if n)
    if inside:
        paras.append(_label("Inside", inside + "."))
    topics = record.get("topics") or []
    if topics and isinstance(topics[0], dict):
        paras.append(_label("1 big thing", topics[0].get("title", "")))
    paras.append("Tap right for the next story, left to go back.")
    return {"kicker": "INFOSECFOLLOW", "headline": "Today's Briefing",
            "paras": [p for p in paras if p], "droppable": []}


def glance_story(glance):
    paras = []
    for e in glance or []:
        kind = "Trend" if e.get("kind") == "Trend" else (
            "New" if e.get("status") == "new" else "Updated")
        line = _label(kind, e.get("text", ""))
        if line:
            paras.append(line)
    return {"kicker": "AT A GLANCE", "headline": "What's Moving Today",
            "paras": paras, "droppable": list(range(1, len(paras)))}


def weather_story(weather):
    return {"kicker": "PITTSBURGH", "headline": "Weather",
            "paras": [to_ascii(w) for w in weather if to_ascii(w)],
            "droppable": list(range(1, len(weather)))}


def scores_story(sports):
    paras = []
    for b in sports or []:
        if not isinstance(b, dict):
            continue
        head = to_ascii(b.get("team"))
        if b.get("record"):
            head += f" ({to_ascii(b['record'])})"
        bits = []
        games = [g for g in (b.get("games") or []) if isinstance(g, dict)]
        if games:
            g = games[-1]
            bits.append(f"{to_ascii(g.get('date'))}: {to_ascii(g.get('result'))}.")
        nxt = b.get("next") if isinstance(b.get("next"), dict) else None
        if nxt:
            bits.append(f"Next: {to_ascii(nxt.get('matchup'))}, {to_ascii(nxt.get('when'))}.")
        if head and bits:
            paras.append(_label(head, " ".join(bits)))
    return {"kicker": "SPORTS", "headline": "Scoreboard", "paras": paras,
            "droppable": list(range(1, len(paras)))}


def reading_story(item):
    paras = [to_ascii(item.get("summary"))]
    return {"kicker": "READING | " + to_ascii(item.get("author")).upper(),
            "headline": to_ascii(item.get("title")),
            "paras": [p for p in paras if p], "droppable": []}


LOCAL_KICKERS = (("business_politics", "Business and Politics"),
                 ("business", "Pittsburgh Business"),
                 ("around_town", "Around Town"),
                 ("events", "Events"))
SPORTS_KICKERS = (("around_teams", "Around the Teams"), ("team_usa", "Team USA"))


def build_stories(record, edition_label):
    digest_topics = [t for t in (record.get("topics") or []) if isinstance(t, dict)]
    local = record.get("local") if isinstance(record.get("local"), dict) else {}
    weather = [w for w in (record.get("weather") or []) if isinstance(w, str)]
    sports = record.get("sports") or []

    body = []
    for t in digest_topics:
        kicker = "Security" + (f" | {t['area']}" if t.get("area") else "")
        body.append(news_story(kicker, t))
    for key, kicker in LOCAL_KICKERS:
        for item in local.get(key) or []:
            if isinstance(item, dict):
                body.append(news_story(kicker, item))
    if weather:
        body.append(weather_story(weather))
    scores = scores_story(sports)
    if scores["paras"]:
        body.append(scores)
    for key, kicker in SPORTS_KICKERS:
        for item in local.get(key) or []:
            if isinstance(item, dict):
                body.append(news_story(kicker, item))
    for item in local.get("reading") or []:
        if isinstance(item, dict):
            body.append(reading_story(item))

    n_local = sum(len(local.get(k) or []) for k, _ in LOCAL_KICKERS)
    n_sports = sum(len(local.get(k) or []) for k, _ in SPORTS_KICKERS)
    counts = [("security", len(digest_topics)), ("business and local", n_local),
              ("sports", n_sports), ("reading", len(local.get("reading") or []))]
    stories = [cover_story(record, edition_label, counts)]
    glance = glance_story(record.get("glance"))
    if glance["paras"]:
        stories.append(glance)
    stories += body
    return [fit_story(s) for s in stories if s["headline"]]


def render_paper(record, edition_label):
    blocks = []
    for s in build_stories(record, edition_label):
        blocks.append("\n".join([s["kicker"], s["headline"], ""] +
                                [p for para in s["paras"] for p in (para, "")]).rstrip() + "\n")
    return "\f\n".join(blocks)
