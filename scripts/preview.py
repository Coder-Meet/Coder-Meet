#!/usr/bin/env python3
"""Render README.md roughly the way GitHub does, to check it before pushing.

    python3 scripts/preview.py                     # writes preview.html (git-ignored)
    python3 scripts/preview.py out.html            # another output file
    python3 scripts/preview.py out.html dark 846   # one panel only: light|dark, content width

preview.html shows the README four times: on a white page and on GitHub dark
(#0d1117), each 830 px wide and 343 px wide. The type is set the way GitHub
sets a profile README (14 px). GitHub's own column was 846 px on a desktop
and 293 to 308 px on a phone when this was written; the images are a fixed
810 px and centred, so they line up the same at any of these widths.

Standard library only. It handles the Markdown this README uses: headings,
paragraphs, bullet lists, inline code, bold, links and raw HTML blocks.
<picture> is resolved per panel, since a single page has only one colour scheme.
"""

import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIDTHS = (830, 343)
THEMES = ("light", "dark")


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def to_html(markdown):
    markdown = re.sub(r"<!--.*?-->", "", markdown, flags=re.S)  # GitHub drops comments
    out, blocks = [], re.split(r"\n\s*\n", markdown.strip())
    for block in blocks:
        lines = [line for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        if lines[0].lstrip().startswith("<"):
            out.append("\n".join(lines))
        elif lines[0].startswith("#"):
            level = len(lines[0]) - len(lines[0].lstrip("#"))
            out.append(f"<h{level}>{inline(lines[0][level:].strip())}</h{level}>")
        elif all(line.startswith("- ") for line in lines):
            out.append("<ul>" + "".join(f"<li>{inline(line[2:])}</li>" for line in lines) + "</ul>")
        else:
            out.append(f"<p>{inline(' '.join(lines))}</p>")
    return "\n".join(out)


def resolve_pictures(body, dark):
    def pick(match):
        block = match.group(0)
        source = re.search(r'<source[^>]*srcset="([^"]+)"[^>]*>', block)
        img = re.search(r"<img[^>]*>", block).group(0)
        if dark and source:
            img = re.sub(r'src="[^"]+"', f'src="{source.group(1)}"', img, count=1)
        return img

    return re.sub(r"<picture>.*?</picture>", pick, body, flags=re.S)


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>README preview</title>
<style>
  body {{ margin: 0; display: flex; flex-wrap: wrap; align-items: flex-start; background: #8b949e; font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif; }}
  .panel {{ padding: 32px; }}
  .light {{ background: #ffffff; color: #1f2328; --link: #0969da; --code: #818b981f; }}
  .dark {{ background: #0d1117; color: #f0f6fc; --link: #4493f8; --code: #656c7633; }}
  .md {{ overflow-wrap: break-word; }}
  .md > :first-child {{ margin-top: 0; }}
  .md > :last-child {{ margin-bottom: 0; }}
  .md p, .md ul {{ margin: 0 0 16px; }}
  .md ul {{ padding-left: 2em; }}
  .md li + li {{ margin-top: .25em; }}
  .md h3 {{ font-size: 1.25em; line-height: 1.25; margin: 24px 0 16px; font-weight: 600; }}
  .md a {{ color: var(--link); text-decoration: none; }}
  .md img {{ max-width: 100%; height: auto; box-sizing: content-box; }}
  .md code {{ font: 85%/1 ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; padding: .2em .4em; background: var(--code); border-radius: 6px; white-space: break-spaces; }}
  .tag {{ font: 11px ui-monospace, Menlo, monospace; opacity: .55; margin: 0 0 12px; letter-spacing: .08em; }}
</style></head><body>
{panels}
</body></html>
"""

PANEL = """<div class="panel {theme}" id="{theme}-{width}"><p class="tag">GITHUB {label} / {width}PX</p><div class="md" style="width: {width}px">{body}</div></div>"""


def main():
    args = sys.argv[1:]
    out = args[0] if args else os.path.join(ROOT, "preview.html")
    themes = (args[1],) if len(args) > 1 else THEMES
    widths = (int(args[2]),) if len(args) > 2 else WIDTHS
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        body = to_html(fh.read())
    if os.path.dirname(os.path.abspath(out)) != ROOT:
        # Rendering outside the repo folder: point images back at it.
        body = body.replace('="assets/', f'="file://{ROOT}/assets/'.replace(" ", "%20"))
    panels = "\n".join(
        PANEL.format(theme=theme, label=theme.upper(), width=width, body=resolve_pictures(body, theme == "dark"))
        for width in widths for theme in themes
    )
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(PAGE.format(panels=panels))
    print("wrote", out)


if __name__ == "__main__":
    main()
