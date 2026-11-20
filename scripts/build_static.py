#!/usr/bin/env python3
"""Build the static README assets: the type outlines, the banner and the project cards.

    pip install fonttools brotli
    python3 scripts/build_static.py              # outlines, banner, cards
    python3 scripts/build_static.py --no-fonts   # banner and cards from the outlines already in glyphs.json

GitHub shows README SVGs through <img>, where web fonts cannot load, so all
type is drawn as outlines. This script reads the font files in scripts/fonts
(the files the site uses, as shipped in the @fontsource packages), pins the
variable fonts to the cuts the site prints with, and writes the outlines,
advance widths, kerning and ligatures to scripts/glyphs.json. Everything,
including the daily contribution chart, is then set from that JSON by
svgkit.py, which needs no font tools.

The contribution calendar is built by contributions.py and the profile
pictures by avatars.py.
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import svgkit  # noqa: E402
from svgkit import CLEAR, GUTTER, LABEL_TRACK, PAD, PAGE, SHEET, THEMES, Svg, columns, face, num, px  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.path.join(HERE, "fonts")
ASSETS = os.path.join(ROOT, "assets")

# ---------------------------------------------------------------- copy

NAMEPLATE = "Meet Patel"
EDITION = ["Vol. 4", "Fall 2026", "Waterloo, Ontario"]
EDITION_DAY, EDITION_NIGHT = "GitHub edition", "Night edition"
STRAP = ["Software engineer", "AI agents and the backends they run on", "University of Waterloo"]
STAMP = ["Open to work", "Summer 2027"]
MONOGRAM = "M"
BANNER_ALT = (
    "Meet Patel. Vol. 4, Fall 2026, Waterloo, Ontario. Software engineer. AI agents and the backends they run on. "
    "University of Waterloo. Open to work, Summer 2027."
)

# One word or phrase of each headline (`spot`) is printed in cobalt, as on the site.
CARDS = [
    {
        "slug": "coursematch",
        "figure": "1",
        "meta": ["Feature 1 of 3", "2026, solo build", "Live at goodbyequest.com"],
        "kicker": "CourseMatch AI",
        "head": "One advisor instead of fifteen browser tabs",
        "spot": "fifteen",
        "standfirst": "An agentic course advisor for University of Waterloo students: 33 tools, 3 tiered LLMs, 6,700+ course catalogs.",
        "credit": ["Python", "FastAPI", "LangGraph", "pgvector", "React"],
    },
    {
        "slug": "medclaw",
        "figure": "2",
        "meta": ["Feature 2 of 3", "2026, at MedMe Health", "Source is private"],
        "kicker": "MedClaw, with Admin Clerk",
        "head": "An agent that operates desktop software on its own",
        "spot": "on its own",
        "standfirst": "A computer-use agent that drives a custom Python RPA system over the Model Context Protocol.",
        "credit": ["Python", "MCP", "RPA", "SQLAlchemy", "Gemini 2.5 Flash (evaluation)"],
    },
    {
        "slug": "twoworlds",
        "figure": "3",
        "meta": ["Feature 3 of 3", "October 2026, team of 4", "Hack the Valley 11"],
        "kicker": "Two Worlds",
        "head": "Ask a city a policy question",
        "spot": "city",
        "standfirst": "Synthetic residents act it out on a mapped stretch of Toronto, and a dashboard compares the world with and without the change.",
        "credit": ["JavaScript", "Python", "Node 22", "LLM agents", "Vultr"],
    },
]

# ---------------------------------------------------------------- type outlines
#
# The faces, as the site sets them:
#   display  Fraunces 600 at its display master: the nameplate
#   mark     Fraunces 600 at optical size 72: the avatar monogram, whose thin
#            stroke has to hold at 40 px
#   figure   Fraunces 500 at its display master: large numerals
#   head     Fraunces 500 at optical size 96: headlines of 24 to 28 px
#   text     Newsreader 400: standfirsts and captions
#   italic   Newsreader 400 italic: the strapline
#   label    IBM Plex Sans Condensed 500: small uppercase labels
#   strong   IBM Plex Sans Condensed 600: the first label in a row, the stamp
#
# Fraunces is pinned with SOFT 0 and WONK 0, and its `rvrn` substitutions are
# applied, which is what gives the plain n, m, h and s the site shows.
# Newsreader gets proportional lining figures, as the site's body text does.
#
# The faces contributions.py sets carry all of ASCII, because its text changes
# every day. The others carry only the letters of the copy above.
#
# The font files are copied unchanged from @fontsource-variable/fraunces,
# @fontsource-variable/newsreader and @fontsource/ibm-plex-sans-condensed
# (all 5.3.0), with their licences beside them.

ASCII = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
FULL = ASCII + "\u00b7\u00d7\u2013\u2018\u2019\u201c\u201d"  # middle dot, times, en dash, curly quotes
FIGURES = " 0123456789,.+-%x/:\u2013"


def letters(*texts):
    return "".join(sorted(set("".join(texts))))


FRAUNCES = "fraunces-latin-full-normal.woff2"
FACES = {
    "display": {"file": FRAUNCES, "axes": {"opsz": 144, "wght": 600, "SOFT": 0, "WONK": 0}, "features": ["rvrn"],
                "chars": letters(NAMEPLATE), "name": "Fraunces 600, optical size 144"},
    "mark": {"file": FRAUNCES, "axes": {"opsz": 72, "wght": 600, "SOFT": 0, "WONK": 0}, "features": ["rvrn"],
             "chars": letters(MONOGRAM), "name": "Fraunces 600, optical size 72"},
    "figure": {"file": FRAUNCES, "axes": {"opsz": 144, "wght": 500, "SOFT": 0, "WONK": 0}, "features": ["rvrn"],
               "chars": FIGURES, "name": "Fraunces 500, optical size 144"},
    "head": {"file": FRAUNCES, "axes": {"opsz": 96, "wght": 500, "SOFT": 0, "WONK": 0}, "features": ["rvrn"],
             "chars": FULL, "name": "Fraunces 500, optical size 96"},
    "text": {"file": "newsreader-latin-opsz-normal.woff2", "axes": {"opsz": 16, "wght": 400}, "features": ["pnum"],
             "chars": FULL, "name": "Newsreader 400, optical size 16"},
    "italic": {"file": "newsreader-latin-opsz-italic.woff2", "axes": {"opsz": 16, "wght": 400}, "features": ["pnum"],
               "chars": letters(*STRAP), "name": "Newsreader 400 italic, optical size 16"},
    "label": {"file": "ibm-plex-sans-condensed-latin-500-normal.woff2", "axes": None, "features": [],
              "chars": FULL, "name": "IBM Plex Sans Condensed 500"},
    "strong": {"file": "ibm-plex-sans-condensed-latin-600-normal.woff2", "axes": None, "features": [],
               "chars": FULL, "name": "IBM Plex Sans Condensed 600"},
}


def _lookups(table, tag):
    """The lookups of one OpenType feature, with extension subtables unwrapped."""
    indices = []
    for record in table.FeatureList.FeatureRecord:
        if record.FeatureTag == tag:
            indices += [i for i in record.Feature.LookupListIndex if i not in indices]
    out = []
    for i in sorted(indices):
        lookup = table.LookupList.Lookup[i]
        out.append([getattr(sub, "ExtSubTable", sub) for sub in lookup.SubTable])
    return out


def _kerning(font, names):
    """Pair kerning between the given glyphs, as {left index: {right index: units}}."""
    if "GPOS" not in font:
        return {}
    index = {name: i for i, name in enumerate(names)}
    out = {}
    for subtables in _lookups(font["GPOS"].table, "kern"):
        done = set()  # within one lookup the first subtable that takes a pair wins
        for sub in subtables:
            if not hasattr(sub, "Coverage") or type(sub).__name__ != "PairPos":
                continue
            covered = {name: i for i, name in enumerate(sub.Coverage.glyphs)}
            for left in names:
                if left not in covered:
                    continue
                if sub.Format == 1:
                    for record in sub.PairSet[covered[left]].PairValueRecord:
                        pair = (left, record.SecondGlyph)
                        if record.SecondGlyph in index and pair not in done:
                            done.add(pair)
                            value = (record.Value1.XAdvance or 0) if record.Value1 else 0
                            if value:
                                out.setdefault(left, {})[record.SecondGlyph] = out.get(left, {}).get(record.SecondGlyph, 0) + value
                else:
                    row = sub.Class1Record[sub.ClassDef1.classDefs.get(left, 0)].Class2Record
                    for right in names:
                        pair = (left, right)
                        if pair in done:
                            continue
                        done.add(pair)
                        value1 = row[sub.ClassDef2.classDefs.get(right, 0)].Value1
                        value = (value1.XAdvance or 0) if value1 else 0
                        if value:
                            out.setdefault(left, {})[right] = out.get(left, {}).get(right, 0) + value
    return {
        str(index[left]): {str(index[right]): value for right, value in sorted(row.items(), key=lambda kv: index[kv[0]]) if value}
        for left, row in sorted(out.items(), key=lambda kv: index[kv[0]])
    }


def _extract(spec):
    from fontTools.pens.basePen import BasePen
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    class PathPen(BasePen):
        """Outline as compact SVG path data in font units, y pointing down."""

        def __init__(self, glyph_set):
            super().__init__(glyph_set)
            self.out = []

        def _moveTo(self, p):
            self.out.append("M%d %d" % (round(p[0]), -round(p[1]) + 0))

        def _lineTo(self, p):
            self.out.append("L%d %d" % (round(p[0]), -round(p[1]) + 0))

        def _qCurveToOne(self, c, p):
            self.out.append("Q%d %d %d %d" % (round(c[0]), -round(c[1]) + 0, round(p[0]), -round(p[1]) + 0))

        def _curveToOne(self, c1, c2, p):
            self.out.append("C%d %d %d %d %d %d" % (
                round(c1[0]), -round(c1[1]) + 0, round(c2[0]), -round(c2[1]) + 0, round(p[0]), -round(p[1]) + 0))

        def _closePath(self):
            self.out.append("Z")

    font = TTFont(os.path.join(FONTS, spec["file"]))
    if spec["axes"]:
        font = instancer.instantiateVariableFont(font, spec["axes"], inplace=False)
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()
    hmtx = font["hmtx"]

    # character to glyph, through the single substitutions of the wanted features
    swaps = {}
    if "GSUB" in font:
        for tag in spec["features"]:
            for subtables in _lookups(font["GSUB"].table, tag):
                for sub in subtables:
                    swaps.update(getattr(sub, "mapping", {}))
    wanted = spec["chars"]
    chars = "".join(ch for ch in wanted if ord(ch) in cmap)
    missing = [ch for ch in wanted if ord(ch) not in cmap]
    if missing:
        print(f"  note: {spec['name']} has no glyph for {' '.join(missing)}")
    names = [swaps.get(cmap[ord(ch)], cmap[ord(ch)]) for ch in chars]

    # standard ligatures between characters we carry
    by_name = {name: ch for ch, name in zip(chars, names)}
    liga = {}
    if "GSUB" in font:
        for subtables in _lookups(font["GSUB"].table, "liga"):
            for sub in subtables:
                for first, ligatures in getattr(sub, "ligatures", {}).items():
                    for lig in ligatures:
                        parts = [first] + list(lig.Component)
                        if all(part in by_name for part in parts):
                            liga["".join(by_name[part] for part in parts)] = len(names)
                            names.append(lig.LigGlyph)

    adv, boxes, outlines = [], [], []
    for name in names:
        pen = PathPen(glyph_set)
        glyph_set[name].draw(pen)
        bounds = BoundsPen(glyph_set)
        glyph_set[name].draw(bounds)
        adv.append(hmtx[name][0])
        outlines.append("".join(pen.out))
        b = bounds.bounds
        boxes.append([round(b[0], 1), round(-b[3], 1), round(b[2], 1), round(-b[1], 1)] if b else None)

    def reach(sample, below=False):
        """How far the ink of these letters goes above the baseline, or below it. Read from the font, carried or not."""
        found = []
        for ch in sample:
            bounds = BoundsPen(glyph_set)
            glyph_set[swaps.get(cmap[ord(ch)], cmap[ord(ch)])].draw(bounds)
            found.append(-bounds.bounds[1] if below else bounds.bounds[3])
        return round(max(found))

    return {
        "name": spec["name"],
        "upm": font["head"].unitsPerEm,
        "cap": reach("H"),
        "xh": reach("x"),
        "fig": reach("0123456789"),
        "asc": reach("bdfhkl"),
        "desc": reach("gjpqy", below=True),
        "chars": chars,
        "liga": liga,
        "adv": adv,
        "box": boxes,
        "d": outlines,
        "kern": _kerning(font, names),
    }


def build_glyphs():
    try:
        import brotli  # noqa: F401  (fontTools needs it to open .woff2)
        import fontTools  # noqa: F401
    except ImportError:
        raise SystemExit("Outlining the fonts needs fontTools and brotli: pip install fonttools brotli")
    data = {
        "about": (
            "Type outlines for the README assets, written by scripts/build_static.py from the fonts in scripts/fonts. "
            "Do not edit. Fraunces, Newsreader and IBM Plex Sans Condensed are under the SIL Open Font License 1.1; "
            "the licences are in scripts/fonts."
        ),
        "faces": {},
    }
    for key, spec in FACES.items():
        data["faces"][key] = _extract(spec)
        print(f"outlined {key:8s} {spec['name']}: {len(data['faces'][key]['d'])} glyphs")
    path = os.path.join(HERE, "glyphs.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, separators=(",", ":"), ensure_ascii=True)
        fh.write("\n")
    svgkit.reload_faces()
    print("wrote", os.path.relpath(path, ROOT), f"({os.path.getsize(path) / 1024:.0f} kB)")


# ---------------------------------------------------------------- banner
#
# The masthead: a sheet with the edition line, the nameplate from margin to
# margin, the double rule, the strapline and the stamp. Drawn in page pixels
# (see svgkit.py), so every rule and baseline sits on a whole pixel. The file
# itself is 1280 px wide; the README shows it at 810.

STAMP_ANGLE = 4  # degrees, anticlockwise


def stamp(svg, t, night):
    """The rubber stamp, drawn about its own centre. Returns (markup, half width, half height)."""
    strong, label = face("strong"), face("label")
    size1, size2 = 14, 10.5
    track1, track2 = 0.1, 0.2
    line1, line2 = (text.upper() for text in STAMP)
    cap1, cap2 = strong.cap / strong.upm * size1, label.cap / label.upm * size2
    a0, _, a1, _ = strong.ink(line1, size1, track1)
    b0, _, b1, _ = label.ink(line2, size2, track2)
    border, gap, inner = 2, 2, 1         # outer line, space, inner line
    pad_x, pad_y, lead = 10, 8.5, 8      # inner line to type; baseline of line 1 to the caps of line 2
    edge = border + gap + inner
    w = max(a1 - a0, b1 - b0) + 2 * (pad_x + edge)
    h = cap1 + lead + cap2 + 2 * (pad_y + edge)
    base1 = -h / 2 + edge + pad_y + cap1
    base2 = base1 + lead + cap2
    spot, paper = t["spot"], t["on_spot"]
    inset = border + gap + inner / 2

    def box(grow, **attrs):
        extra = "".join(f' {key.replace("_", "-")}="{value}"' for key, value in attrs.items())
        return (f'<rect x="{num(-w / 2 + grow)}" y="{num(-h / 2 + grow)}" width="{num(w - 2 * grow)}" '
                f'height="{num(h - 2 * grow)}"{extra}/>')

    if night:
        # at night the second ink prints solid and the type is knocked out of it
        body = box(0, fill=spot) + box(inset, fill="none", stroke=paper, stroke_width=num(inner))
        ink = paper
    else:
        body = (box(border / 2, fill="none", stroke=spot, stroke_width=num(border))
                + box(inset, fill="none", stroke=spot, stroke_width=num(inner)))
        ink = spot
    body += svg.text(strong, line1, 0, base1, size1, ink, anchor="middle", tracking=track1, flush=True)
    body += svg.text(label, line2, 0, base2, size2, ink, anchor="middle", tracking=track2, flush=True)
    return body, w / 2, h / 2


def banner(theme):
    t = THEMES[theme]
    night = theme == "dark"
    W, M = SHEET, PAD
    right = W - M
    col, _ = columns(M, right, 12, GUTTER)
    display, italic, label, strong = (face(key) for key in ("display", "italic", "label", "strong"))

    # vertical positions, top to bottom
    strip_base = M + 8                  # 11 px labels: their caps start at the padding
    strip_rule = strip_base + 8
    x0, y0, x1, _ = display.ink(NAMEPLATE, 1)
    name_size = (right - M) / (x1 - x0)                   # the ink runs from margin to margin
    name_base = px(strip_rule + 1 + 14 - y0 * name_size)  # 14 under the hairline, then the tallest letter
    rule = name_base + 13               # double rule: 3 px, 2 px of paper, 1 px
    band = rule + 6                     # the strapline's band starts under the double rule
    close = band + 55                   # closing hairline
    H = close + 1 + M

    svg = Svg(W, H, BANNER_ALT)
    svg.size = (1280, round(1280 * (H + 2 * CLEAR) / PAGE, 2))
    svg.style = (
        ".stamp{animation:press .7s cubic-bezier(.3,.6,.3,1) 1.2s 1 both}"
        "@keyframes press{0%,100%{transform:none}30%{transform:scale(1.06)}55%{transform:scale(.985)}}"
        "@media (prefers-reduced-motion:reduce){.stamp{animation:none}}"
    )
    svg.sheet(t)

    # Folio strip: the edition line on columns 1, 4, 8 and 11, closed by a hairline.
    edition = EDITION + [EDITION_NIGHT if night else EDITION_DAY]
    for i, (c, text) in enumerate(zip((0, 3, 7, 10), edition)):
        svg.put(strong if i == 0 else label, text.upper(), col[c], strip_base, 11, t["ink"] if i == 0 else t["mid"],
                tracking=LABEL_TRACK, flush=True)
    svg.rule(M, right, strip_rule, 1, t["ink"])

    # Nameplate, then the double rule.
    svg.put(display, NAMEPLATE, M, name_base, name_size, t["ink"], flush=True)
    svg.rule(M, right, rule, 3, t["ink"])
    svg.rule(M, right, rule + 5, 1, t["ink"])

    # Strapline on columns 1, 4 and 8, centred in its band on the x-height, then the closing hairline.
    strap_size = 14
    strap_base = px((band + close) / 2 + italic.xh / italic.upm * strap_size / 2)
    for c, text in zip((0, 3, 7), STRAP):
        svg.put(italic, text, col[c], strap_base, strap_size, t["ink"], flush=True)
    svg.rule(M, right, close, 1, t["ink"])

    # The stamp, across the double rule, which carries on for 10 beyond it to
    # the margin. Its lowest corner is 5 clear of the closing hairline. It is
    # pressed once, a second after loading: the animation starts and ends on
    # the finished picture, so a still is complete, and it is switched off
    # for readers who ask for reduced motion.
    body, half_w, half_h = stamp(svg, t, night)
    sin, cos = math.sin(math.radians(STAMP_ANGLE)), math.cos(math.radians(STAMP_ANGLE))
    reach_x, reach_y = half_w * cos + half_h * sin, half_w * sin + half_h * cos
    cx, cy = right - 10 - reach_x, close - 5 - reach_y
    assert cy - reach_y * 1.06 > name_base + 4, "the stamp would touch the nameplate, even mid-press"
    assert col[7] + italic.width(STRAP[2], strap_size) < cx - reach_x - 16, "the stamp would crowd the strapline"
    for a, b, text in zip((0, 3), (3, 7), STRAP):
        assert col[a] + italic.width(text, strap_size) < col[b] - 16, f"{text!r} runs into the next column"
    blend = "" if night else ' style="mix-blend-mode:multiply"'  # over the rule like a second ink
    svg.add(f'<g transform="translate({num(cx)} {num(cy)}) rotate({-STAMP_ANGLE})"{blend}><g class="stamp">{body}</g></g>')

    return svg.render()


# ---------------------------------------------------------------- cards
#
# Three small features, shown at their natural size (270 px wide): three to a
# row on a desktop, one to a row on a phone. In the README the three images
# sit edge to edge, so the row is exactly as wide as the banner, and the boxes
# share its sheet's edges.

CARD_W, CARD_H = 262, 340
assert 3 * (CARD_W + 2 * CLEAR) == PAGE, "three cards should be as wide as the banner"


def card(theme, spec):
    t = THEMES[theme]
    night = theme == "dark"
    W, H, P = CARD_W, CARD_H, PAD
    inner = W - 2 * P
    figure, head, text, label, strong = (face(key) for key in ("figure", "head", "text", "label", "strong"))
    title = f'{spec["figure"]}. {spec["kicker"]}. {spec["head"]}. {spec["standfirst"]} Built with {", ".join(spec["credit"])}.'
    svg = Svg(W, H, title)
    svg.box(t)

    def fits(fc, line, size, tracking=0.0, width=inner):
        left, _, right, _ = fc.ink(line, size, tracking)
        assert right - left <= width, f'{spec["slug"]}: {line!r} is too wide'
        return line

    # The numeral, its ink 60 high, with the feature's particulars beside it
    # on three hairlines. The first hairline is level with the top of the
    # numeral and the last line of type stands level with its foot.
    fig_h, pitch = 60, 22
    foot = P + fig_h
    _, top, _, bottom = figure.ink(spec["figure"], 1)
    fig_size = fig_h / (bottom - top)
    svg.put(figure, spec["figure"], P, P - top * fig_size, fig_size, t["ink"], flush=True)
    meta_x = P + 60
    for i, line in enumerate(spec["meta"]):
        y = P + i * pitch
        svg.rule(meta_x, W - P, y, 1, t["hair"])
        svg.put(strong if i == 0 else label, fits(strong, line.upper(), 11, LABEL_TRACK, W - P - meta_x), meta_x,
                y + pitch - 6, 11, t["ink"] if i == 0 else t["mid"], tracking=LABEL_TRACK, flush=True)

    # Kicker, headline and standfirst flow down from the numeral.
    y = foot + 26
    svg.put(strong, fits(strong, spec["kicker"].upper(), 11, LABEL_TRACK), P, y, 11, t["ink"], tracking=LABEL_TRACK, flush=True)
    size, lead, track = 25, 27, -0.008
    spot = spec["spot"].replace(" ", "\u00a0")  # the highlighted words stay on one line
    y += px(11 + head.cap / head.upm * size)
    for line in head.wrap(spec["head"].replace(spec["spot"], spot), size, inner, track, balance=True):
        before, hit, after = fits(head, line, size, track).partition(spot)
        if not hit:
            svg.put(head, line, P, y, size, t["ink"], tracking=track, flush=True)
        elif night:
            # at night the second ink prints solid and the type is knocked out of it
            markup, spans = svg.runs(head, [(before, t["ink"]), (hit, t["on_spot"]), (after, t["ink"])], P, y, size, track, flush=True)
            x0, x1 = spans[1]
            svg.rect(x0 - 3, y - 20, x1 - x0 + 6, 27, t["spot"])
            svg.add(markup)
        else:
            svg.add(svg.runs(head, [(before, t["ink"]), (hit, t["spot"]), (after, t["ink"])], P, y, size, track, flush=True)[0])
        y += lead
    y += px(13 + text.cap / text.upm * 15) - lead
    for line in text.wrap(spec["standfirst"], 15, inner):
        svg.put(text, fits(text, line, 15), P, y, 15, t["ink"])
        y += 20

    # The credit, pinned to the foot of the box: a label, then the stack on two lines.
    stack = ", ".join(item.replace(" ", "\u00a0") for item in spec["credit"]).upper()  # an item never breaks
    credit = label.wrap(stack, 11, inner, LABEL_TRACK)
    assert len(credit) == 2, f'{spec["slug"]}: the credit should set in two lines, not {len(credit)}'
    base = H - P - 1 - len(credit) * 15    # 1 more, for the commas that hang under the last line
    rule_y = base - 18
    assert y - 20 + 5 <= rule_y - 8, f'{spec["slug"]}: the standfirst runs into the credit'
    svg.rule(P, W - P, rule_y, 1, t["hair"])
    svg.put(label, "BUILT WITH", P, base, 11, t["mid"], tracking=LABEL_TRACK, flush=True)
    for i, line in enumerate(credit):
        svg.put(label, fits(label, line, 11, LABEL_TRACK), P, base + (i + 1) * 15, 11, t["ink"], tracking=LABEL_TRACK, flush=True)

    return svg.render()


def write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print("wrote", os.path.relpath(path, ROOT), f"({len(text) / 1024:.1f} kB)")


def main():
    if "--no-fonts" not in sys.argv:
        build_glyphs()
    os.makedirs(ASSETS, exist_ok=True)
    for theme in ("light", "dark"):
        write(os.path.join(ASSETS, f"banner-{theme}.svg"), banner(theme))
    for spec in CARDS:
        for theme in ("light", "dark"):
            write(os.path.join(ASSETS, f"card-{spec['slug']}-{theme}.svg"), card(theme, spec))


if __name__ == "__main__":
    main()
