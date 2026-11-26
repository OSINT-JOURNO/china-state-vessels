#!/usr/bin/env python3
"""Draw assets/banner.svg, the animated banner at the top of the README, from data/vessels.csv.

Every number on the banner (vessels per group, the date checked) is read from the CSV, so re-run this after
tools/build.py whenever the data changes. The banner is plain SVG animation: no scripts, no external files, so GitHub
shows it. Text is drawn as outlines, so it looks the same whatever fonts the viewer has. The ring shows one tick per
vessel, grouped; it is a count, not a map, and no tick stands for a position.

Needs: pip install fonttools, and JetBrains Mono (SIL Open Font License) as a variable .ttf.
Run:   python3 tools/make_banner.py /path/to/JetBrainsMono.ttf
"""
import csv
import math
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "vessels.csv")
OUT = os.path.join(ROOT, "assets", "banner.svg")

# The four groups, in README order. Colours were checked for colour-blind separation and contrast on the background.
GROUPS = [("research and survey", "R", "#0fa697"), ("PLA", "N", "#c97800"), ("coast guard", "C", "#3b82f6"),
          ("named as militia", "M", "#ec4899")]
PREFIX = {"research": "R", "survey": "R", "space_tracking": "N", "intelligence": "N", "navy_survey": "N",
          "coast_guard": "C", "militia": "M"}
LINES = ["every row cites its sources", "militia labels name who made them", "blank means not established, never none",
         "MMSIs looked up in the ITU ship register", "data free to reuse under CC BY 4.0"]

W, H = 1200, 340
CX, CY, R = 190, 170, 112          # the ring
TX, TY = 412, 196                  # the typed line
SLOT = 3.6                         # seconds per typed line
LOOP = 10.0                        # seconds per ring cycle
FILL = 5.0                         # seconds to light every tick
BG, GRID, TEAL, AMBER, TEXT, DIM = "#0b1016", "#16202b", "#2dd4bf", "#fbbf24", "#e6edf3", "#7d8b99"


def f(x):
    return f"{x:.4f}".rstrip("0").rstrip(".")


def read_counts(path=DATA):
    """Vessels per group and the latest last_checked date, from the CSV."""
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    counts = {key: 0 for _, key, _ in GROUPS}
    for row in rows:
        counts[PREFIX[row["category"]]] += 1
    checked = max(date.fromisoformat(row["last_checked"]) for row in rows)
    return counts, len(rows), checked


def label(counts, total, checked):
    """The banner's text alternative; also what the tests compare with the CSV."""
    parts = ", ".join(f"{counts[key]} {name}" for name, key, _ in GROUPS)
    return (f"China state-linked vessels, an open dataset by OSINT JOURNO: {total} vessels ({parts}), "
            f"last checked {checked.day} {checked.strftime('%B %Y')}")


def build(font_file):
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen

    fonts = {}

    def outline(text, x, y, size, weight=400, spacing=0.0):
        if weight not in fonts:
            ft = instantiateVariableFont(TTFont(font_file), {"wght": weight})
            fonts[weight] = (ft.getGlyphSet(), ft.getBestCmap(), ft["hmtx"])
        gs, cmap, hmtx = fonts[weight]
        k, pen, cx = size / 1000, SVGPathPen(gs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip(".")), x
        for ch in text:
            name = cmap[ord(ch)]
            gs[name].draw(TransformPen(pen, (k, 0, 0, -k, cx, y)))
            cx += hmtx[name][0] * k + spacing
        return pen.getCommands(), cx - x - spacing

    def T(text, x, y, size, fill, weight=400, spacing=0.0, extra=""):
        d, w = outline(text, x, y, size, weight, spacing)
        return f'<path d="{d}" fill="{fill}"{extra}/>', w

    counts, total, checked = read_counts()
    alt = label(counts, total, checked)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="{alt}">', f"<title>{alt}</title>",
         f'''<defs>
<clipPath id="card"><rect width="{W}" height="{H}" rx="18"/></clipPath>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{GRID}" stroke-width="1"/></pattern>
<radialGradient id="glow" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="{TEAL}" stop-opacity=".12"/><stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></radialGradient>
<linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="{BG}" stop-opacity="0"/><stop offset=".25" stop-color="{BG}" stop-opacity="0"/><stop offset="1" stop-color="{BG}" stop-opacity=".9"/></linearGradient>
</defs>''',
         f'<g clip-path="url(#card)"><rect width="{W}" height="{H}" fill="{BG}"/><rect width="{W}" height="{H}" fill="url(#grid)"/>'
         f'<rect width="{W}" height="{H}" fill="url(#fade)"/>',
         f'<circle cx="{CX}" cy="{CY}" r="{R + 40}" fill="url(#glow)"/>',
         f'<circle cx="{CX}" cy="{CY}" r="{R - 26}" fill="none" stroke="{TEAL}" stroke-opacity=".18" stroke-width="1"/>']

    # The ring: one tick per vessel, groups in order, one empty slot between groups. Ticks light up one after another
    # (clockwise from the top), hold, then fade together before the next cycle. There is deliberately no radar-style
    # sweep arm: the ring is a count, not a screen of positions.
    slots, gap = [], 0
    for _, key, colour in GROUPS:
        slots += [colour] * counts[key] + [None]
    step = 360 / len(slots)
    fade_a, fade_b = (LOOP - 1.0) / LOOP, (LOOP - 0.4) / LOOP
    for i, colour in enumerate(slots):
        if colour is None:
            continue
        ang = math.radians(-90 + (i + 0.5) * step)
        x0, y0 = CX + (R - 16) * math.cos(ang), CY + (R - 16) * math.sin(ang)
        x1, y1 = CX + R * math.cos(ang), CY + R * math.sin(ang)
        t = (i + 0.5) / len(slots) * FILL / LOOP
        o.append(f'<line x1="{f(x0)}" y1="{f(y0)}" x2="{f(x1)}" y2="{f(y1)}" stroke="{colour}" stroke-width="3.2" '
                 f'stroke-linecap="round" opacity=".12"><animate attributeName="opacity" values=".12;.12;1;1;.12;.12" '
                 f'keyTimes="0;{f(t)};{f(min(t + .01, fade_a - .01))};{f(fade_a)};{f(fade_b)};1" dur="{f(LOOP)}s" '
                 f'repeatCount="indefinite"/></line>')
    num, nw = outline(str(total), 0, 0, 64, 800)
    o.append(T(str(total), CX - nw / 2, CY + 14, 64, TEXT, 800)[0])
    _, vw = outline("VESSELS", 0, 0, 14, 600, 2.2)
    o.append(T("VESSELS", CX - vw / 2, CY + 42, 14, DIM, 600, 2.2)[0])

    # text
    o.append(T("// OSINT JOURNO  ·  OPEN DATASET", TX - 32, 78, 17, TEAL, 500, 1.6)[0])
    o.append(T("CHINA STATE-LINKED VESSELS", TX - 34, 138, 42, TEXT, 800, 2)[0])
    o.append(T(">", TX - 32, TY, 24, AMBER, 700)[0])
    period = SLOT * len(LINES)
    for i, line in enumerate(LINES):
        el, w = T(line, TX, TY, 24, TEXT, 400, 0, f' clip-path="url(#c{i})"')
        w += 5
        a, b, c, d = i * SLOT, i * SLOT + 1.1, (i + 1) * SLOT - .45, (i + 1) * SLOT - .1   # type in, hold, wipe out
        kt = ";".join(f(x / period) for x in ((0, a, b, c, d, period) if i else (0, b, c, d, period)))
        wv = f"0;0;{f(w)};{f(w)};0;0" if i else f"0;{f(w)};{f(w)};0;0"
        xv = ";".join(f(TX + float(x)) for x in wv.split(";"))
        ov = "0;1;1;1;0;0" if i else "1;1;1;0;0"
        o.append(f'<clipPath id="c{i}"><rect x="{TX}" y="{TY - 24}" height="34" width="0"><animate attributeName="width" '
                 f'values="{wv}" keyTimes="{kt}" dur="{f(period)}s" repeatCount="indefinite"/></rect></clipPath>'
                 f'{el}<rect y="{TY - 19}" width="11" height="24" fill="{AMBER}" opacity="0"><animate attributeName="x" '
                 f'values="{xv}" keyTimes="{kt}" dur="{f(period)}s" repeatCount="indefinite"/><animate attributeName="opacity" '
                 f'values="{ov}" keyTimes="{kt}" dur="{f(period)}s" calcMode="discrete" repeatCount="indefinite"/></rect>')

    # the key: a colour square beside each group, numbers and names in text colours
    # largest size (up to 19 px) at which the whole key fits inside the card
    items = [f"{counts[key]} {name}" for name, key, _ in GROUPS]
    size = 19.0
    while size > 12 and sum(outline(t, 0, 0, size, 500)[1] for t in items) + len(items) * (size * 1.15 + 1.6 * size) - 1.6 * size > W - 36 - (TX - 32):
        size -= 0.5
    x, y, box, gap = TX - 32, 256, size * .74, size * 1.6
    for text, (name, key, colour) in zip(items, GROUPS):
        o.append(f'<rect x="{f(x)}" y="{f(y - box)}" width="{f(box)}" height="{f(box)}" rx="2" fill="{colour}"/>')
        el, w = T(text, x + size * 1.15, y, size, TEXT, 500)
        o.append(el)
        x += size * 1.15 + w + gap
    assert x - gap <= W - 36, "key does not fit"
    o.append(T(f"every row dated  ·  last checked {checked.day} {checked.strftime('%b %Y')}  ·  github.com/OSINT-JOURNO",
               TX - 32, 302, 16.5, DIM)[0])
    o.append("</g></svg>")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(o) + "\n")
    print(f"{os.path.relpath(OUT, ROOT)}: {os.path.getsize(OUT)} bytes; {alt}")
    return x


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "JetBrainsMono.ttf")
