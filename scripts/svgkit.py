"""Shared kit for the profile README assets, set in the style of The Report.

Paper, ink and one spot colour, on a simple grid, with all type drawn as
outlines.

GitHub shows README images through <img>, where web fonts cannot load. So none
of the text in these SVGs is live text: every glyph is an outline taken from
the typefaces the site uses and kept in glyphs.json, which build_static.py
writes from the font files. This module only reads that JSON, so it needs
nothing beyond the standard library and the daily CI job can import it as is.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GLYPHS = os.path.join(HERE, "glyphs.json")

# ---------------------------------------------------------------- tokens
#
# The same values as the site's main.css. Greys are ink printed lighter on the
# stock: 60% for secondary labels, 25% for hairlines, 12% for the edge of a
# sheet. The night edition swaps the stock and the ink and keeps the cobalt;
# its sheet edge is the 25% grey, because 12% is lost on GitHub's dark page.

PAPER = "#f4f1ea"
INK = "#111110"
COBALT = "#1f3bff"

THEMES = {
    "light": {
        "page": PAPER,
        "ink": INK,
        "mid": "#6c6b67",    # ink at 60%
        "hair": "#bbb9b4",   # ink at 25%
        "edge": "#d9d6cf",   # ink at 12%
        "spot": COBALT,
        "on_spot": PAPER,
        # the dot chart: no activity, then three greys of ink
        "dots": ["#bbb9b4", "#7d7c78", "#474643", INK],
    },
    "dark": {
        "page": INK,
        "ink": PAPER,
        "mid": "#999793",    # paper at 60%
        "hair": "#4a4947",   # paper at 25%
        "edge": "#4a4947",   # paper at 25%
        "spot": COBALT,
        "on_spot": PAPER,
        "dots": ["#4a4947", "#888682", "#c4c2bc", PAPER],
    },
}

# Letter-spacing of the small uppercase labels, as on the site (0.06em).
LABEL_TRACK = 0.06

# The page. Every image is drawn in the pixels it is shown at and none of them
# is fluid: the banner and the chart are 810 px wide, each card is a third of
# that, and the README centres them. So whatever width GitHub gives the column
# (846 px on a desktop when this was drawn, and it has changed before), the
# sheets and the cards share their edges, and a rule drawn 1 px thick is 1 px
# thick. On a phone the banner and the chart shrink to fit and the cards stack.
#
# Each image carries a 4 px clear margin, so cards that wrap never touch.
# Inside a sheet or a card the contents keep 20 px from the edge, which puts
# the type of the first and last card on the same lines as the banner's.
PAGE = 810
CLEAR = 4
SHEET = PAGE - 2 * CLEAR
PAD = 20
GUTTER = 16


def px(value):
    """Round to a whole pixel, halves upwards."""
    return int(value + 0.5) if value >= 0 else -int(-value + 0.5)


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def num(value):
    """Short number formatting for SVG attributes."""
    text = ("%.2f" % value).rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


# ---------------------------------------------------------------- type

class Face:
    """One typeface at one weight and optical size, read from glyphs.json.

    Sizes are in SVG user units (px). Tracking is in em, like CSS
    letter-spacing. Kerning is always applied. Ligatures are applied only to
    untracked text, which is what browsers do.
    """

    def __init__(self, key, data):
        self.key = key
        self.name = data["name"]
        self.upm = data["upm"]
        self.cap = data["cap"]        # height of H
        self.xh = data["xh"]          # height of x
        self.fig = data["fig"]        # height of the tallest figure
        self.asc = data["asc"]        # height of the tallest ascender
        self.desc = data["desc"]      # depth of the deepest descender
        self.adv = data["adv"]
        self.box = data["box"]        # ink box per glyph, y pointing down, or None
        self.d = data["d"]            # outline per glyph in font units, y pointing down
        self._index = {ch: i for i, ch in enumerate(data["chars"])}
        self._liga = sorted(data.get("liga", {}).items(), key=lambda item: -len(item[0]))
        self._kern = {int(a): {int(b): v for b, v in row.items()} for a, row in data.get("kern", {}).items()}

    def glyphs(self, text, ligatures=True):
        """Text to glyph indices."""
        text = text.replace("\u00a0", " ")
        out, i = [], 0
        while i < len(text):
            if ligatures:
                hit = next(((seq, g) for seq, g in self._liga if text.startswith(seq, i)), None)
                if hit:
                    out.append(hit[1])
                    i += len(hit[0])
                    continue
            ch = text[i]
            if ch not in self._index:
                raise KeyError(
                    f"{ch!r} is not in glyphs.json for the {self.key!r} face. "
                    "Add it to that face's chars in build_static.py and rebuild."
                )
            out.append(self._index[ch])
            i += 1
        return out

    def shape(self, text, tracking=0.0, ligatures=None):
        """Return ([(glyph, x)], advance), both in font units.

        Ligatures default to on for untracked text and off for tracked text.
        """
        track = tracking * self.upm
        x, prev, placed = 0.0, None, []
        for g in self.glyphs(text, ligatures=not tracking if ligatures is None else ligatures):
            if prev is not None:
                x += self._kern.get(prev, {}).get(g, 0) + track
            placed.append((g, x))
            x += self.adv[g]
            prev = g
        return placed, x

    def width(self, text, size, tracking=0.0):
        """Advance width, without trailing letter-spacing."""
        return self.shape(text, tracking)[1] * size / self.upm

    def ink(self, text, size, tracking=0.0):
        """Ink box (x0, y0, x1, y1) relative to the text origin, y pointing down."""
        scale = size / self.upm
        boxes = [(x, self.box[g]) for g, x in self.shape(text, tracking)[0] if self.box[g]]
        if not boxes:
            return 0.0, 0.0, 0.0, 0.0
        return (
            min(x + b[0] for x, b in boxes) * scale,
            min(b[1] for _, b in boxes) * scale,
            max(x + b[2] for x, b in boxes) * scale,
            max(b[3] for _, b in boxes) * scale,
        )

    def wrap(self, text, size, max_width, tracking=0.0, balance=False):
        """Break text into lines no wider than max_width.

        With balance, the lines are evened out (as CSS text-wrap: balance does)
        without adding a line.
        """
        words = [word for word in text.split(" ") if word]  # a no-break space does not break

        def fill(limit):
            lines, line = [], ""
            for word in words:
                trial = f"{line} {word}" if line else word
                if line and self.width(trial, size, tracking) > limit:
                    lines.append(line)
                    line = word
                else:
                    line = trial
            return lines + [line] if line else lines

        lines = fill(max_width)
        if any(self.width(line, size, tracking) > max_width for line in lines):
            raise ValueError(f"a word in {text!r} is wider than {max_width:.0f}px at {size}px")
        if balance and len(lines) > 1:
            lo, hi = max_width / len(lines), max_width
            for _ in range(24):
                mid = (lo + hi) / 2
                trial = fill(mid)
                fits = len(trial) <= len(lines) and all(self.width(line, size, tracking) <= mid for line in trial)
                lo, hi = (lo, mid) if fits else (mid, hi)
            lines = fill(hi)
        return lines


_faces = {}


def face(key):
    """Load a face from glyphs.json (once)."""
    if not _faces:
        if not os.path.exists(GLYPHS):
            raise SystemExit("scripts/glyphs.json is missing. Run: python3 scripts/build_static.py")
        with open(GLYPHS, encoding="utf-8") as fh:
            for name, data in json.load(fh)["faces"].items():
                _faces[name] = Face(name, data)
    return _faces[key]


def reload_faces():
    """Forget the loaded faces (build_static.py calls this after rewriting glyphs.json)."""
    _faces.clear()


# ---------------------------------------------------------------- drawing

class Svg:
    """A small SVG builder. Each glyph outline is defined once and reused.

    The drawing is width by height, with `clear` of nothing around it.
    """

    def __init__(self, width, height, title, clear=CLEAR):
        self.width, self.height, self.title, self.clear = width, height, title, clear
        self.size = None    # the file's own size, if not the size of the drawing
        self.style = ""
        self._body = []
        self._ids = {}
        self._prefix = {}

    def add(self, markup):
        self._body.append(markup)
        return self

    def _glyph(self, fc, g):
        if (fc.key, g) not in self._ids:
            prefix = self._prefix.setdefault(fc.key, "abcdefghijklmnopqrstuvwxyz"[len(self._prefix)])
            count = sum(1 for key, _ in self._ids if key == fc.key)
            self._ids[(fc.key, g)] = f"{prefix}{count}"
        return self._ids[(fc.key, g)]

    def _line(self, fc, placed, x, y, size, fill, attrs=""):
        uses = "".join(
            f'<use xlink:href="#{self._glyph(fc, g)}"' + (f' x="{round(gx)}"' if round(gx) else "") + "/>"
            for g, gx in placed if fc.d[g]
        )
        return f'<g transform="translate({num(x)} {num(y)}) scale({size / fc.upm:.6g})" fill="{fill}"{attrs}>{uses}</g>'

    def text(self, fc, text, x, y, size, fill, anchor="start", tracking=0.0, flush=False, attrs=""):
        """Markup for one line of outlined text with its baseline at y.

        anchor is start, middle or end. It is measured on the advance width,
        the way a browser places text, or on the ink itself with flush=True,
        which puts the first or last stroke exactly on x.
        """
        placed, advance = fc.shape(text, tracking)
        left, right = (fc.ink(text, size, tracking)[0::2]) if flush else (0.0, advance * size / fc.upm)
        if anchor == "end":
            x -= right
        elif anchor == "middle":
            x -= (left + right) / 2
        else:
            x -= left
        return self._line(fc, placed, x, y, size, fill, attrs)

    def put(self, fc, text, x, y, size, fill, anchor="start", tracking=0.0, flush=False, attrs=""):
        """Set one line of text on the drawing. Returns its advance width."""
        self._body.append(self.text(fc, text, x, y, size, fill, anchor, tracking, flush, attrs))
        return fc.width(text, size, tracking)

    def runs(self, fc, parts, x, y, size, tracking=0.0, flush=False):
        """Markup for one line made of [(text, fill)] runs, kerned as a single line.

        Returns (markup, [(x0, x1)]): the ink extent of each run, so a caller
        can draw behind one. Ligatures are not formed, so every character is
        one glyph.
        """
        scale = size / fc.upm
        placed, _ = fc.shape("".join(part for part, _ in parts), tracking, ligatures=False)
        if flush:
            x -= min((gx + fc.box[g][0]) * scale for g, gx in placed if fc.box[g])
        markup, spans, start = "", [], 0
        for part, fill in parts:
            chunk = placed[start:start + len(part)]
            start += len(part)
            inked = [(gx + fc.box[g][0], gx + fc.box[g][2]) for g, gx in chunk if fc.box[g]]
            if not inked:
                spans.append((x, x))
                continue
            markup += self._line(fc, chunk, x, y, size, fill)
            spans.append((x + min(a for a, _ in inked) * scale, x + max(b for _, b in inked) * scale))
        return markup, spans

    def rect(self, x, y, width, height, fill, attrs=""):
        self._body.append(
            f'<rect x="{num(x)}" y="{num(y)}" width="{num(width)}" height="{num(height)}" fill="{fill}"{attrs}/>'
        )
        return self

    def rule(self, x0, x1, y, weight, fill, attrs=""):
        """A horizontal rule from x0 to x1 with its top edge at y."""
        return self.rect(x0, y, x1 - x0, weight, fill, attrs)

    def render(self):
        defs = "".join(
            f'<path id="{gid}" d="{face(key).d[g]}"/>'
            for (key, g), gid in sorted(self._ids.items(), key=lambda item: (item[1][0], int(item[1][1:])))
        )
        style = f"<style>{self.style}</style>" if self.style else ""
        outer = (self.width + 2 * self.clear, self.height + 2 * self.clear)
        width, height = self.size or outer
        body = "".join(self._body)
        if self.clear:
            body = f'<g transform="translate({num(self.clear)} {num(self.clear)})">{body}</g>'
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{num(width)}" height="{num(height)}" viewBox="0 0 {num(outer[0])} {num(outer[1])}" '
            f'role="img" aria-label="{esc(self.title)}">'
            f"<title>{esc(self.title)}</title>{style}<defs>{defs}</defs>{body}</svg>"
        )

    def sheet(self, t):
        """The stock, with a hairline edge so the sheet reads as a sheet on any page."""
        self.rect(0, 0, self.width, self.height, t["page"])
        self.add(f'<rect x="0.5" y="0.5" width="{num(self.width - 1)}" height="{num(self.height - 1)}" '
                 f'fill="none" stroke="{t["edge"]}"/>')
        return self

    def box(self, t):
        """A boxed item: the stock inside a 1 px line of ink."""
        self.rect(0, 0, self.width, self.height, t["page"])
        self.add(f'<rect x="0.5" y="0.5" width="{num(self.width - 1)}" height="{num(self.height - 1)}" '
                 f'fill="none" stroke="{t["ink"]}"/>')
        return self


def columns(left, right, count, gutter):
    """Left edges of `count` equal columns between two margins, and the column width."""
    width = (right - left - gutter * (count - 1)) / count
    return [left + i * (width + gutter) for i in range(count)], width
