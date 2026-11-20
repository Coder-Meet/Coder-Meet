#!/usr/bin/env python3
"""Build the contribution calendar: assets/contributions-{dark,light}.svg

The calendar is printed the way the site prints it: one dot per day, larger
the busier the day, in greys of ink, with the busiest day in cobalt.

Standard library only, so it runs as it is in GitHub Actions. The type is set
from scripts/glyphs.json (see build_static.py).

    Local:  python3 scripts/contributions.py        (uses the gh CLI's login)
    CI:     GITHUB_TOKEN=... python3 scripts/contributions.py

Private contributions: with your own gh login the total includes them. The
default Actions token only sees them if "Private contributions" is turned on
in your GitHub profile settings; otherwise the number drops to public only.
"""

import json
import math
import os
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svgkit import GUTTER, LABEL_TRACK, PAD, SHEET, THEMES, Svg, columns, face, num, px  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOGIN = os.environ.get("GH_LOGIN", "Coder-Meet")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date weekday contributionCount } }
      }
    }
  }
}
"""

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# dates in running text follow AP style, as on the site
AP_MONTHS = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]


def fetch(login):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
        request = urllib.request.Request(
            "https://api.github.com/graphql",
            data=body,
            headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-readme"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    else:
        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={QUERY}", "-F", f"login={login}"],
            check=True, capture_output=True, text=True,
        )
        payload = json.loads(result.stdout)
    if payload.get("errors"):
        raise SystemExit(f"GitHub API error: {payload['errors']}")
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def ap_date(iso):
    """Oct. 28, 2026, held together with no-break spaces so a line never ends inside it."""
    year, month, day = (int(part) for part in iso.split("-"))
    return f"{AP_MONTHS[month - 1]}\u00a0{day},\u00a0{year}"


def plural(count, word):
    return f"{count:,} {word}" if count == 1 else f"{count:,} {word}s"


def dot_radius(count, peak):
    """Radius in a cell 10 units wide: the site's formula.

    A day with nothing is a speck. Any other day gets a smallest printable dot
    plus the square root of its share of the busiest day, so the area of the
    dot follows the count.
    """
    if count <= 0:
        return 0.75
    return 1.15 + 3.55 * math.sqrt(count / peak)


def dot_fill(count, peak, t):
    """Greys of ink by quarter of the busiest day. Cobalt is kept for the busiest day itself."""
    if count <= 0:
        return t["dots"][0]
    if count == peak:
        return t["spot"]
    return t["dots"][min(3, math.ceil(4 * count / peak))]


def render(calendar, theme, login=LOGIN):
    t = THEMES[theme]
    figure, head, text, label, strong = (face(key) for key in ("figure", "head", "text", "label", "strong"))
    weeks = calendar["weeks"]
    days = [day for week in weeks for day in week["contributionDays"]]
    total = calendar["totalContributions"]
    active = sum(1 for day in days if day["contributionCount"] > 0)
    peak = max((day["contributionCount"] for day in days), default=0)
    busiest = [day for day in days if peak and day["contributionCount"] == peak]
    first, last = days[0]["date"], days[-1]["date"]

    # A sheet as wide as the banner's, on the same padding and the same twelve
    # columns, drawn in page pixels (see svgkit.py).
    W, M = SHEET, PAD
    col, col_w = columns(M, W - M, 12, GUTTER)
    right = W - M
    pitch = (right - M) / len(weeks)       # one cell per week, across the measure

    # vertical positions, top to bottom; rules and baselines sit on whole pixels
    label_base = M + 1 + px(10 + label.cap / label.upm * 11)   # 10 under the top rule
    head_size, head_lead = 28, 31
    count_top = label_base + 20
    count_base = count_top + head_lead + px(head.cap / head.upm * head_size)   # as tall as two lines of headline
    months_base = count_base + px(22 + label.cap / label.upm * 11)
    grid_top = months_base + 8
    grid_bottom = grid_top + 7 * pitch
    rule_y = px(grid_bottom + 12)
    cap_size, cap_lead = 14, 19
    cap_base = rule_y + 1 + px(12 + text.cap / text.upm * cap_size)

    # caption, in three columns of four
    span = col[3] + col_w - col[0]
    key_r = 5.5
    if busiest:
        if len(busiest) == 1:
            first_note = f"Busiest day: {plural(peak, 'contribution')} on {ap_date(busiest[0]['date'])}, printed in cobalt."
        else:
            first_note = f"Busiest days: {plural(peak, 'contribution')} each, on {len(busiest)} days, printed in cobalt."
    else:
        first_note = "No contributions in this period yet."
    notes = [
        text.wrap(first_note, cap_size, span - (2 * key_r + 7 if busiest else 0)),
        text.wrap("The larger the dot, the busier the day. Weeks run left to right, and days Sunday to Saturday, top to bottom.", cap_size, span),
        text.wrap(f"Source: github.com/{login}", cap_size, span),
    ]
    hang = math.ceil(text.desc / text.upm * cap_size)          # the padding is kept clear of descenders
    H = cap_base + (max(len(lines) for lines in notes) - 1) * cap_lead + hang + M

    title = (
        f"{plural(total, 'GitHub contribution')} in the last twelve months, on {plural(active, 'active day')}, "
        f"drawn as one dot per day from {ap_date(first)} to {ap_date(last)}."
        + (f" {first_note.replace(', printed in cobalt', '')}" if busiest else "")
    )
    svg = Svg(W, H, title.replace("\u00a0", " "))
    svg.sheet(t)

    # running head: a rule, then small labels on the columns
    svg.rule(M, right, M, 1, t["ink"])
    svg.put(strong, "CHART 1", M, label_base, 11, t["ink"], tracking=LABEL_TRACK, flush=True)
    svg.put(label, "ONE DOT PER DAY", col[3], label_base, 11, t["mid"], tracking=LABEL_TRACK, flush=True)
    svg.put(label, f"{ap_date(first)} to {ap_date(last)}".upper(), right, label_base, 11, t["mid"],
            anchor="end", tracking=LABEL_TRACK, flush=True)

    # the count, then the headline that finishes its sentence
    count = f"{total:,}"
    count_size = (count_base - count_top) * figure.upm / figure.cap
    svg.put(figure, count, M, count_base, count_size, t["ink"], flush=True)
    x0, _, x1, _ = figure.ink(count, count_size)
    head_x = next((x for x in col[3:] if x >= M + (x1 - x0) + 16), col[-4])
    sentence = f"GitHub contributions in the last twelve months, on {plural(active, 'active day')}"
    for size in (head_size, 26, 24, 22, 20, 18):   # a very long count leaves less room: set smaller, never taller
        lines = head.wrap(sentence, size, right - head_x, -0.008, balance=True)
        if len(lines) <= 2:
            break
    lines = lines[:2]
    for i, line in enumerate(lines):
        base = count_base - (len(lines) - 1 - i) * head_lead
        svg.put(head, line, head_x, base, size, t["ink"], tracking=-0.008, flush=True)

    # months: the name sits over the week that holds the first of the month
    for i, week in enumerate(weeks):
        for day in week["contributionDays"]:
            if day["date"].endswith("-01"):
                name = MONTHS[int(day["date"][5:7]) - 1].upper()
                x = min(M + i * pitch, right - label.ink(name, 11, LABEL_TRACK)[2])
                svg.put(label, name, x, months_base, 11, t["mid"], tracking=LABEL_TRACK, flush=True)

    # the dots
    by_fill = {}
    for i, week in enumerate(weeks):
        for day in week["contributionDays"]:
            n = day["contributionCount"]
            cx = M + (i + 0.5) * pitch
            cy = grid_top + (day["weekday"] + 0.5) * pitch
            by_fill.setdefault(dot_fill(n, peak, t), []).append(
                f'<circle cx="{num(cx)}" cy="{num(cy)}" r="{num(dot_radius(n, peak) * pitch / 10)}"/>'
            )
    order = t["dots"] + [t["spot"]]
    for fill in sorted(by_fill, key=order.index):
        svg.add(f'<g fill="{fill}">' + "".join(by_fill[fill]) + "</g>")

    # caption
    svg.rule(M, right, rule_y, 1, t["hair"])
    for c, block in zip((0, 4, 8), notes):
        x = col[c]
        if c == 0 and busiest:
            svg.add(f'<circle cx="{num(x + key_r)}" cy="{num(cap_base - text.xh / text.upm * cap_size / 2)}" r="{num(key_r)}" fill="{t["spot"]}"/>')
        indent = 2 * key_r + 7 if (c == 0 and busiest) else 0   # the first note hangs from its key
        for i, line in enumerate(block):
            svg.put(text, line, x + indent, cap_base + i * cap_lead, cap_size, t["ink"])

    return svg.render()


def main():
    calendar = fetch(LOGIN)
    for theme in ("dark", "light"):
        path = os.path.join(ROOT, "assets", f"contributions-{theme}.svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render(calendar, theme) + "\n")
        print("wrote", os.path.relpath(path, ROOT))
    print(f'{calendar["totalContributions"]:,} contributions across {len(calendar["weeks"])} weeks for {LOGIN}')


if __name__ == "__main__":
    main()
