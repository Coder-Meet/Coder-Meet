#!/usr/bin/env python3
"""Build the profile pictures in avatar/ (1024 x 1024 PNG, upload one by hand).

    pip install pillow
    python3 scripts/avatars.py [path/to/meet-cutout-bust.webp]

    avatar-photo.png        the cut-out bust in black and white on flat cobalt
    avatar-photo-paper.png  the same on paper
    avatar-mark.png         the M of the nameplate, paper on cobalt

The cut-out is used as it is: its matte is not touched, only scaled. The
photographs are skipped if the cut-out is not found. avatar-photo-color.png is
not built here and is left alone.
"""

import os
import re
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svgkit import COBALT, PAPER, face  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "avatar")
CUTOUT = os.path.join(ROOT, "..", "_studio", "shared", "img", "meet-cutout-bust.webp")
SIZE = 1024


def rgb(hex_colour):
    return tuple(int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))


# ---------------------------------------------------------------- photographs
#
# GitHub crops the picture to a circle, so the head sits inside the circle and
# is large enough to read at 40 px. The cut-out is cropped hard along its
# bottom edge and where the shoulder meets its right edge, so it is scaled and
# placed to run off the picture on both of those sides.

HEAD = (462, 235)        # centre of the head in the 800 px cut-out
HEAD_AT = (548, 424)     # where that point goes in the picture
SCALE = 1.43


def black_and_white(cutout):
    """The black plate: luminance, then a firmer curve so it holds at small sizes."""
    r, g, b, alpha = cutout.split()
    grey = Image.merge("RGB", (r, g, b)).convert("L")

    def curve(v):
        x = min(max((v - 10) / 232.0, 0.0), 1.0)      # set the black and white points
        x = x * x * (3 - 2 * x) * 0.55 + x * 0.45      # a gentle S
        return round(255 * x)

    return grey.point([curve(v) for v in range(256)]), alpha


def photo(cutout, background):
    grey, alpha = black_and_white(cutout)
    figure = Image.merge("RGBA", (grey, grey, grey, alpha))
    side = round(cutout.width * SCALE)
    # premultiplied, so nothing from outside the matte bleeds into its edge
    figure = figure.convert("RGBa").resize((side, round(cutout.height * SCALE)), Image.LANCZOS).convert("RGBA")
    left = round(HEAD_AT[0] - HEAD[0] * SCALE)
    top = round(HEAD_AT[1] - HEAD[1] * SCALE)
    assert left + figure.width >= SIZE and top + figure.height >= SIZE, "the hard edges of the cut-out would show"
    picture = Image.new("RGBA", (SIZE, SIZE), rgb(background) + (255,))
    picture.alpha_composite(figure, (max(left, 0), max(top, 0)), (max(-left, 0), max(-top, 0)))
    return picture.convert("RGB")


# ---------------------------------------------------------------- monogram

def contours(d, steps=24):
    """Flatten SVG path data (M, L, Q, C, Z with absolute coordinates) into polygons."""
    out, current, pen = [], [], (0.0, 0.0)
    for command, body in re.findall(r"([MLQCZ])([^MLQCZ]*)", d):
        n = [float(v) for v in body.split()]
        if command == "M":
            if current:
                out.append(current)
            pen = (n[0], n[1])
            current = [pen]
        elif command == "L":
            pen = (n[0], n[1])
            current.append(pen)
        elif command == "Q":
            (x0, y0), (x1, y1), (x2, y2) = pen, (n[0], n[1]), (n[2], n[3])
            for i in range(1, steps + 1):
                t = i / steps
                current.append(((1 - t) ** 2 * x0 + 2 * (1 - t) * t * x1 + t * t * x2,
                                (1 - t) ** 2 * y0 + 2 * (1 - t) * t * y1 + t * t * y2))
            pen = (x2, y2)
        elif command == "C":
            (x0, y0), (x1, y1), (x2, y2), (x3, y3) = pen, (n[0], n[1]), (n[2], n[3]), (n[4], n[5])
            for i in range(1, steps + 1):
                t = i / steps
                current.append(((1 - t) ** 3 * x0 + 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t * t * x2 + t ** 3 * x3,
                                (1 - t) ** 3 * y0 + 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t * t * y2 + t ** 3 * y3))
            pen = (x3, y3)
        elif command == "Z" and current:
            out.append(current)
            current = []
    if current:
        out.append(current)
    return out


def fill_nonzero(shapes, size):
    """Rasterise polygons with the non-zero winding rule, as a browser fills a glyph.

    Outlines from a variable font overlap themselves, and Pillow's own polygon
    fill (even-odd) would leave those overlaps empty.
    """
    edges = []
    for points in shapes:
        for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]):
            if y0 != y1:
                edges.append((min(y0, y1), max(y0, y1), x0, y0, (x1 - x0) / (y1 - y0), 1 if y1 > y0 else -1))
    edges.sort()
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    live, nxt = [], 0
    for row in range(size):
        y = row + 0.5
        while nxt < len(edges) and edges[nxt][0] <= y:
            live.append(edges[nxt])
            nxt += 1
        live = [edge for edge in live if edge[1] > y]
        winding, start = 0, None
        for x, turn in sorted((x0 + (y - y0) * slope, turn) for _, _, x0, y0, slope, turn in live):
            if winding == 0:
                start = x
            winding += turn
            if winding == 0 and x > start:
                draw.line([(round(start), row), (round(x) - 1, row)], fill=255)
    return mask


def mark(letters="M", width=0.6, over=4):
    """The monogram, centred on its ink, `width` of the picture wide."""
    display = face("mark")
    placed, _ = display.shape(letters)
    x0, y0, x1, y1 = (v * display.upm for v in display.ink(letters, 1))
    full = SIZE * over
    scale = full * width / (x1 - x0)
    dx = (full - (x1 - x0) * scale) / 2 - x0 * scale
    dy = (full - (y1 - y0) * scale) / 2 - y0 * scale
    shapes = [
        [(dx + (gx + x) * scale, dy + y * scale) for x, y in points]
        for g, gx in placed for points in contours(display.d[g])
    ]
    mask = fill_nonzero(shapes, full).resize((SIZE, SIZE), Image.LANCZOS)
    picture = Image.new("RGB", (SIZE, SIZE), rgb(COBALT))
    picture.paste(Image.new("RGB", (SIZE, SIZE), rgb(PAPER)), (0, 0), mask)
    return picture


def save(picture, name):
    path = os.path.join(OUT, name)
    picture.save(path, optimize=True)
    print("wrote", os.path.relpath(path, ROOT), picture.size)


def main():
    os.makedirs(OUT, exist_ok=True)
    source = sys.argv[1] if len(sys.argv) > 1 else CUTOUT
    if os.path.exists(source):
        cutout = Image.open(source).convert("RGBA")
        save(photo(cutout, COBALT), "avatar-photo.png")
        save(photo(cutout, PAPER), "avatar-photo-paper.png")
    else:
        print("no cut-out at", source, "- skipping the photographs")
    save(mark(), "avatar-mark.png")


if __name__ == "__main__":
    main()
