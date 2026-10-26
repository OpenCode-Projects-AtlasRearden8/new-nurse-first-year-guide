#!/usr/bin/env python3
"""Build the New Nurse First-Year Guide static site from markdown sources.

Local-first, standard library only: no network calls, no dependencies, no
analytics. Every generated page carries the education-only / not-medical-advice
banner and the LLC copyright footer.

Usage:
    python3 build.py                # build into ./site and validate links
    python3 build.py --out DIR      # build into a chosen directory
    python3 build.py --check-only   # validate sources without writing
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"
WORKSHEETS_DIR = ROOT / "worksheets"
DEFAULT_OUT = ROOT / "site"

SITE_TITLE = "New Nurse: The First-Year Survival Guide"
SITE_TAGLINE = "Education only — not medical advice"
DISCLAIMER_PHRASES = ("Education only", "not medical advice")
BANNER_TEXT = "Education only — this guide is never medical advice."
FOOTER_TEXT = (
    "Copyright (c) 2026 Asdale Dynamics, LLC · MIT License · "
    "Education only — not medical advice."
)

CHAPTER_BLURBS = {
    "00-read-me-first": "How to use this guide, and the disclaimers that matter.",
    "01-orientation-expectations": "What orientation is for, and what “done” looks like.",
    "02-asking-questions": "Scripts that make asking easy, sorted by the moment.",
    "03-organizing-report-notes": "A report sheet that survives all twelve hours.",
    "04-preceptors-and-feedback": "Feedback as fuel: the bar, the gap, the stretch.",
    "05-night-shift-survival": "Sleep blocks, caffeine leases, and the drive-home plan.",
    "06-confidence-math": "Why comfort arrives near shift 100 — tracked honestly.",
    "07-burnout-warning-signs": "Amber lights, caught while they are still cheap to fix.",
    "08-when-to-switch-units": "Hard stretch versus wrong fit — a sorting tool.",
    "09-glossary": "The words they will use on day one, translated.",
}

WORKSHEET_BLURBS = {
    "shift-worksheet": "One-page brain sheet with decision-shaped watch-fors.",
    "night-shift-worksheet": "Plan the sleep, caffeine, food, and drive-home logistics.",
    "confidence-log": "Track 100 shifts; watch the trend, not perfection.",
    "burnout-check": "The two-minute Sunday mirror, with read-it rules.",
    "feedback-notes": "Log every piece of feedback — your receipts for later.",
}

STYLE = """\
:root {
  --paper: #faf7f0; --ink: #2b2925; --soft: #6f6759;
  --accent: #2e6e5b; --accent-soft: #e3efe8; --line: #e4dccb;
  --card: #ffffff; --warn-bg: #fdf1e2; --warn-ink: #8a5a19;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--paper); color: var(--ink);
  font: 17px/1.65 Georgia, "Iowan Old Style", "Times New Roman", serif;
}
.layout { max-width: 56rem; margin: 0 auto; padding: 0 1.2rem 3.5rem; }
header.topbar {
  position: sticky; top: 0; z-index: 5;
  background: var(--paper); border-bottom: 1px solid var(--line);
}
.topbar-inner {
  max-width: 56rem; margin: 0 auto; padding: .7rem 1.2rem;
  display: flex; align-items: baseline; justify-content: space-between; gap: 1rem;
}
.topbar a.home { font-weight: 700; color: var(--ink); text-decoration: none; }
.topbar a.home:hover { color: var(--accent); }
.topbar .tag { color: var(--warn-ink); font-size: .8rem; }
.banner {
  margin: 1rem auto 0; max-width: 56rem; padding: .55rem .9rem;
  background: var(--warn-bg); color: var(--warn-ink);
  border: 1px solid #f0d9b8; border-radius: 8px; font-size: .9rem;
}
main { padding-top: .5rem; }
.card {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 12px; padding: 1.1rem 1.35rem; margin: 1rem 0;
}
h1 { font-size: 2rem; line-height: 1.25; margin: 1.6rem 0 .6rem; }
h2 { font-size: 1.3rem; margin-top: 2rem; border-bottom: 1px solid var(--line); padding-bottom: .25rem; }
h3 { font-size: 1.05rem; margin-top: 1.4rem; }
p { margin: .6rem 0; }
a { color: var(--accent); }
table { border-collapse: collapse; width: 100%; margin: .8rem 0; font-size: .93rem; }
th, td { border: 1px solid var(--line); padding: .45rem .6rem; text-align: left; vertical-align: top; }
th { background: var(--accent-soft); font-family: system-ui, sans-serif; font-size: .85rem; }
code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: .86em; }
pre {
  background: #f3efe6; border: 1px solid var(--line); border-radius: 8px;
  padding: .8rem 1rem; overflow-x: auto; line-height: 1.5;
}
code { background: #f3efe6; padding: .08em .3em; border-radius: 4px; }
pre code { background: none; padding: 0; }
blockquote {
  margin: .8rem 0; padding: .2rem .9rem; border-left: 4px solid var(--accent);
  background: var(--accent-soft); border-radius: 0 8px 8px 0;
}
blockquote p { margin: .4rem 0; }
ul, ol { margin: .5rem 0; padding-left: 1.6rem; }
ol ul, ul ul { margin: .2rem 0; }
li { margin: .25rem 0; }
hr { border: none; border-top: 1px solid var(--line); margin: 1.8rem 0; }
.tagline { color: var(--soft); font-style: italic; margin-top: -.2rem; }
.disclaimer-box {
  background: var(--warn-bg); border: 1px solid #f0d9b8; border-radius: 10px;
  padding: .8rem 1rem; margin: 1rem 0; color: var(--warn-ink); font-size: .95rem;
}
.toc-list { list-style: none; padding: 0; }
.toc-list li { margin: .55rem 0; }
.toc-list a { text-decoration: none; font-weight: 700; font-size: 1.02rem; }
.toc-list a:hover { text-decoration: underline; }
.blurb { color: var(--soft); font-size: .92rem; display: block; margin-top: .1rem; }
footer.site {
  border-top: 1px solid var(--line); margin-top: 2.5rem; padding: 1rem 0 0;
  text-align: center; color: var(--soft); font-size: .85rem;
}
nav.pager { display: flex; justify-content: space-between; gap: 1rem; margin-top: 2rem; }
nav.pager a { text-decoration: none; font-weight: 700; }
nav.pager .next { margin-left: auto; text-align: right; }
@media (max-width: 640px) { body { font-size: 16px; } h1 { font-size: 1.6rem; } }
@media print {
  header.topbar, .banner, nav.pager, footer.site { display: none; }
  body { background: #fff; font-size: 12pt; }
  pre { white-space: pre-wrap; }
}
"""


# --------------------------------------------------------------------------
# Minimal markdown renderer (the subset used by docs/ and worksheets/)
# --------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^```(\w*)\s*$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_HR_RE = re.compile(r"^(?:-{3,}|\*{3,})\s*$")
_LIST_RE = re.compile(r"^(\s*)([-*])\s+(.*)$")
_OLIST_RE = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_TABLE_ROW_RE = re.compile(r"^\|.*\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?(?::?\s*-{3,}\s*:?\|)+\s*$")
_QUOTE_RE = re.compile(r"^>\s?(.*)$")

_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


def _inline(text: str, resolver=None) -> str:
    """Render inline markdown: code spans, links, bold, italic."""
    out = _esc(text)
    stash: list[str] = []
    link_parts: list[tuple[str, str]] = []

    out = _INLINE_CODE_RE.sub(
        lambda m: _hold(stash, "<code>" + _esc(m.group(1).strip()) + "</code>"), out
    )

    def link_repl(m: re.Match[str]) -> str:
        link_parts.append((m.group(1), m.group(2).strip()))
        return _hold(stash, f"\x01link{len(link_parts) - 1}\x01")

    out = _LINK_RE.sub(link_repl, out)
    out = _BOLD_RE.sub(lambda m: "<strong>" + m.group(1) + "</strong>", out)
    out = _ITALIC_RE.sub(lambda m: "<em>" + m.group(1) + "</em>", out)

    def restore(m: re.Match[str]) -> str:
        value = stash[int(m.group(1))]
        if value.startswith("\x01link"):
            label_raw, target = link_parts[int(value[len("\x01link"):-1])]
            resolved = resolver(target) if resolver else target
            resolved = _esc(resolved)
            return '<a href="' + resolved + '">' + _inline(label_raw, resolver) + "</a>"
        return value

    return re.sub(r"\x00tok(\d+)\x00", restore, out)


def _hold(stash: list[str], value: str) -> str:
    stash.append(value)
    return f"\x00tok{len(stash) - 1}\x00"


def _checkbox(item_text: str) -> str:
    if item_text.startswith("[ ]"):
        return '<span class="cb">☐</span>' + item_text[3:]
    if item_text.startswith(("[x] ", "[X] ")):
        return '<span class="cb">☑</span>' + item_text[4:]
    return item_text


def _split_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [c.strip() for c in stripped.split("|")]


def render_markdown(text: str, resolver=None) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if _FENCE_RE.match(stripped):
            buf: list[str] = []
            i += 1
            while i < n and not lines[i].lstrip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + _esc("\n".join(buf)) + "</code></pre>")
            continue

        heading = _HEADING_RE.match(stripped)
        if heading:
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline(heading.group(2), resolver)}</h{level}>")
            i += 1
            continue

        if _HR_RE.match(stripped):
            out.append("<hr>")
            i += 1
            continue

        if _QUOTE_RE.match(stripped):
            quote_buf: list[str] = []
            while i < n and (q := _QUOTE_RE.match(lines[i].strip())):
                quote_buf.append(q.group(1))
                i += 1
            content = "<br>".join(_inline(q, resolver) for q in quote_buf if q.strip())
            out.append(f"<blockquote><p>{content}</p></blockquote>")
            continue

        if _TABLE_ROW_RE.match(stripped) and i + 1 < n and _TABLE_SEP_RE.match(lines[i + 1].strip()):
            header = _split_row(line)
            i += 2
            rows: list[list[str]] = []
            while i < n and _TABLE_ROW_RE.match(lines[i].strip()) and not _TABLE_SEP_RE.match(lines[i].strip()):
                rows.append(_split_row(lines[i]))
                i += 1
            thead = "".join(f"<th>{_inline(c, resolver)}</th>" for c in header)
            body = "".join(
                "<tr>" + "".join(f"<td>{_inline(c, resolver)}</td>" for c in row) + "</tr>"
                for row in rows
            )
            out.append(f"<table><thead><tr>{thead}</tr></thead><tbody>{body}</tbody></table>")
            continue

        if _LIST_RE.match(line) or _OLIST_RE.match(line):
            ordered = _OLIST_RE.match(line) is not None
            items: list[tuple[str, list[tuple[str, str | None]]]] = []
            while i < n and lines[i].strip():
                l = lines[i]
                outer = _OLIST_RE.match(l) if ordered else _LIST_RE.match(l)
                if outer:
                    items.append((outer.group(3).strip(), []))
                    i += 1
                    continue
                inner = _LIST_RE.match(l) if ordered else _OLIST_RE.match(l)
                if inner and l[:1].isspace() and items:
                    # nested list: tag type follows the inner marker, not the outer
                    inner_ordered = _OLIST_RE.match(l) is not None
                    items[-1][1].append((inner.group(3).strip(), "ol" if inner_ordered else "ul"))
                    i += 1
                    continue
                if l[:1].isspace() and items and not _FENCE_RE.match(l.strip()):
                    items[-1][1].append((l.strip(), None))
                    i += 1
                    continue
                break
            tag = "ol" if ordered else "ul"
            rendered = []
            for text_, subs in items:
                label = _inline(_checkbox(text_), resolver)
                subhtml = ""
                if subs:
                    sub_kind = "ol" if any(k == "ol" for _, k in subs) else "ul"
                    subitems = "".join(
                        f"<li>{_inline(_checkbox(s), resolver)}</li>" for s, k in subs if k
                    )
                    conts = "".join(f" {_inline(s, resolver)}" for s, k in subs if k is None)
                    subhtml = f"<{sub_kind}>{subitems}</{sub_kind}>{conts}"
                rendered.append(f"<li>{label}{subhtml}</li>")
            out.append(f"<{tag}>" + "".join(rendered) + f"</{tag}>")
            continue

        para = [stripped]
        i += 1
        while i < n:
            nxt = lines[i].strip()
            if (
                not nxt
                or _FENCE_RE.match(nxt)
                or _HEADING_RE.match(nxt)
                or _HR_RE.match(nxt)
                or _QUOTE_RE.match(nxt)
                or _TABLE_ROW_RE.match(nxt)
                or _LIST_RE.match(nxt)
                or _OLIST_RE.match(nxt)
            ):
                break
            para.append(nxt)
            i += 1
        out.append("<p>" + _inline(" ".join(para), resolver) + "</p>")

    return "\n".join(out)


def extract_title(markdown_text: str) -> str:
    for line in markdown_text.splitlines():
        m = _HEADING_RE.match(line.strip())
        if m and m.group(1) == "#":
            return re.sub(r"<[^>]+>", "", _inline(m.group(2)))
    return "Untitled"


# --------------------------------------------------------------------------
# Site generation
# --------------------------------------------------------------------------

class Page:
    """One output HTML page built from a markdown source."""

    def __init__(self, source: Path, kind: str):
        self.source = source
        self.slug = source.stem
        self.kind = kind
        self.markdown = source.read_text(encoding="utf-8")
        self.title = extract_title(self.markdown)
        self.out_dir = "chapters" if kind == "chapters" else "worksheets"
        self.filename = self.slug + ".html"
        self.nav_html = ""

    def body_html(self) -> str:
        def resolver(target: str) -> str:
            t = target.strip()
            if t.startswith(("http://", "https://", "#", "mailto:")):
                return t
            bucket, name = None, t
            for prefix, target_bucket in (
                ("../docs/", "chapters"),
                ("docs/", "chapters"),
                ("../worksheets/", "worksheets"),
                ("worksheets/", "worksheets"),
            ):
                if t.startswith(prefix):
                    bucket, name = target_bucket, t[len(prefix):]
                    break
            if bucket is None:
                if t.endswith(".html"):
                    bucket, name = "chapters", t
                else:
                    return t
            wanted = Path(bucket) / name
            return os.path.relpath(wanted, Path(self.out_dir)).replace(os.sep, "/")

        return render_markdown(self.markdown, resolver)

    def toc_entry(self, blurbs: dict[str, str]) -> str:
        blurb = blurbs.get(self.slug, "")
        href = os.path.relpath(Path(self.out_dir) / self.filename, Path("")).replace(os.sep, "/")
        blurb_html = f'<span class="blurb">{blurb}</span>' if blurb else ""
        return f'<li><a href="{href}">{self.title}</a>{blurb_html}</li>'


def page_shell(page_title: str, body: str, *, home_href: str, extra_head: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; base-uri 'none'; form-action 'none'">
<meta name="description" content="{_esc(SITE_TITLE)} — education only, never medical advice. {_esc(page_title)}">
<title>{_esc(page_title)} — {_esc(SITE_TITLE)}</title>
{extra_head}
</head>
<body>
<header class="topbar"><div class="topbar-inner">
<a class="home" href="{home_href}">{_esc(SITE_TITLE)}</a>
<span class="tag">{_esc(SITE_TAGLINE)}</span>
</div></header>
<div class="banner">{BANNER_TEXT}</div>
<div class="layout">
{body}
<footer class="site">{FOOTER_TEXT}</footer>
</div>
</body>
</html>
"""


def toc_list(pages: list[Page], blurbs: dict[str, str], base: str = "") -> str:
    items = []
    for p in pages:
        href = base + p.out_dir + "/" + p.filename
        blurb = blurbs.get(p.slug, "")
        blurb_html = f'<span class="blurb">{blurb}</span>' if blurb else ""
        items.append(f'<li><a href="{href}">{p.title}</a>{blurb_html}</li>')
    return '<ul class="toc-list">' + "\n".join(items) + "</ul>"


def build_index(chapters: list[Page], worksheets: list[Page]) -> str:
    hero = (
        '<main><div class="hero"><h1>' + _esc(SITE_TITLE) + "</h1>"
        '<p class="tagline">Plain-English, tested, local-first — '
        "written the way a friend would explain it.</p></div>"
    )
    disclaimer = (
        '<div class="disclaimer-box"><strong>Education only — never medical advice.</strong> '
        "This guide teaches habits, checklists, and self-management. It does not teach "
        "clinical care and never overrides your facility's policies, your state practice "
        "act, or your clinical team. When in doubt, the policy manual and your escalation "
        "chain come first.</div>"
    )
    quick = (
        '<div class="card"><strong>Short on time?</strong> Start with '
        '<a href="chapters/06-confidence-math.html">confidence math</a> to calm down, '
        '<a href="chapters/03-organizing-report-notes.html">report notes</a> to get organized, '
        'then the <a href="worksheets/index.html">worksheets</a> to keep it going.</div>'
    )
    body = (
        hero
        + disclaimer
        + quick
        + "<h2>Chapters</h2>" + toc_list(chapters, CHAPTER_BLURBS)
        + "<h2>Worksheets</h2>" + toc_list(worksheets, WORKSHEET_BLURBS)
        + '<p><a href="worksheets/index.html">All worksheets on one page →</a></p>'
        + "<h2>Related projects</h2>"
        + '<div class="card"><p>This guide complements its sibling tools, built in the same '
        "local-first spirit:</p><ul>"
        "<li><strong>nclex-style-quiz-trainer</strong> — practice-style quizzes for "
        "license-exam study and knowledge refresh.</li>"
        "<li><strong>sbar-report-builder-webapp</strong> — builds SBAR handoff reports in a "
        'form; pairs naturally with <a href="chapters/03-organizing-report-notes.html">'
        "the report-notes chapter</a>.</li></ul></div></main>"
    )
    return page_shell("Read this first", body, home_href="index.html", extra_head="<style>\n" + STYLE + "</style>")


def build_worksheets_index(worksheets: list[Page]) -> str:
    heading = (
        '<main><h1>Worksheets</h1>'
        "<p>Printable, local-first companions to the guide. Every sheet is blank by "
        "design: no patient identifiers belong on personal paper, and anything that "
        "must be recorded goes where your facility's policy says it goes.</p></main>"
    )
    body = heading + toc_list(worksheets, WORKSHEET_BLURBS, base="../") + (
        '<main><div class="card"><strong>Printing tip:</strong> every page is print-styled — '
        "banners and nav drop away, wide blocks wrap. Ctrl/Cmd+P works in any browser, "
        "offline, from any machine.</div>"
        '<p><a href="../index.html">← Back to contents</a></p></main>'
    )
    return page_shell("Worksheets", body, home_href="../index.html", extra_head="<style>\n" + STYLE + "</style>")


def build_chapter_page(page: Page) -> str:
    index_href = os.path.relpath("index.html", page.out_dir).replace(os.sep, "/")
    body = f'<main>\n{page.body_html()}\n{page.nav_html}\n<footer class="site">{FOOTER_TEXT}</footer>\n</main>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; base-uri 'none'; form-action 'none'">
<meta name="description" content="{_esc(SITE_TITLE)} — education only, never medical advice. {_esc(page.title)}">
<title>{_esc(page.title)} — {_esc(SITE_TITLE)}</title>
<meta name="robots" content="noindex">
</head>
<body>
<header class="topbar"><div class="topbar-inner">
<a class="home" href="{index_href}">{_esc(SITE_TITLE)}</a>
<span class="tag">{_esc(SITE_TAGLINE)}</span>
</div></header>
<div class="banner">{BANNER_TEXT}</div>
{body}
</body>
</html>
"""


def set_nav_chains(chapters: list[Page], worksheets: list[Page]) -> None:
    for pages_list in (chapters, worksheets):
        for idx, page in enumerate(pages_list):
            parts = []
            if idx > 0:
                prev_ = pages_list[idx - 1]
                href = os.path.relpath(
                    Path(prev_.out_dir) / prev_.filename, Path(page.out_dir)
                ).replace(os.sep, "/")
                parts.append(f'<span class="prev">← <a href="{href}">{prev_.title}</a></span>')
            if idx + 1 < len(pages_list):
                nxt = pages_list[idx + 1]
                href = os.path.relpath(
                    Path(nxt.out_dir) / nxt.filename, Path(page.out_dir)
                ).replace(os.sep, "/")
                parts.append(f'<span class="next"><a href="{href}">{nxt.title}</a> →</span>')
            if not parts:
                index_back = os.path.relpath("index.html", page.out_dir).replace(os.sep, "/")
                parts.append(f'<span class="prev"><a href="{index_back}">← Back to contents</a></span>')
            page.nav_html = '<nav class="pager">' + "".join(parts) + "</nav>"


def collect_pages() -> tuple[list[Page], list[Page]]:
    chapters = [Page(p, "chapters") for p in sorted(DOCS_DIR.glob("*.md"))]
    worksheets = [Page(p, "worksheets") for p in sorted(WORKSHEETS_DIR.glob("*.md"))]
    return chapters, worksheets


def check_sources(chapters: list[Page], worksheets: list[Page]) -> list[str]:
    """Validation that applies to the sources, not the output."""
    problems: list[str] = []
    for page in chapters + worksheets:
        rel = page.source.relative_to(ROOT)
        if not any(phrase in page.markdown for phrase in DISCLAIMER_PHRASES):
            problems.append(f"{rel}: missing disclaimer phrase ('Education only' / 'not medical advice')")
        if page.title == "Untitled":
            problems.append(f"{rel}: no top-level (h1) title found")
    if len(chapters) < 9:
        problems.append(f"expected at least 9 chapters, found {len(chapters)}")
    if len(worksheets) < 5:
        problems.append(f"expected at least 5 worksheets, found {len(worksheets)}")

    # source-side link sanity: every internal link target must map to a markdown
    # source, or be one of the generated index pages
    href_re = re.compile(r"\]\(([^)]+)\)")
    for page in chapters + worksheets:
        for target in href_re.findall(page.markdown):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            name = Path(target).name
            if target.startswith(("../docs/", "docs/")):
                base = DOCS_DIR
            elif target.startswith(("../worksheets/", "worksheets/")):
                base = WORKSHEETS_DIR
            else:
                base = page.source.parent
            candidate = base / name.replace(".html", ".md")
            if not candidate.exists() and name != "index.html":
                problems.append(f"{page.source.relative_to(ROOT)}: dead internal target {target}")
    return problems


def validate_site_links(site_dir: Path) -> list[str]:
    """Every href in every generated page must exist inside the built site."""

    href_re = re.compile(r'(?:href|src)="([^"]+)"')
    problems: list[str] = []
    for html_file in sorted(site_dir.rglob("*.html")):
        text = html_file.read_text(encoding="utf-8")
        for target in href_re.findall(text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            resolved = (html_file.parent / target).resolve()
            if not resolved.exists():
                rel_path = html_file.relative_to(site_dir)
                problems.append(f"{rel_path}: broken internal link {target}")
    return problems


def build(out_dir: Path | None = None, check_only: bool = False) -> list[str]:
    chapters, worksheets = collect_pages()
    problems = check_sources(chapters, worksheets)
    if problems or check_only:
        return problems

    out = Path(out_dir or DEFAULT_OUT)
    if out.exists():
        shutil.rmtree(out)
    (out / "chapters").mkdir(parents=True)
    (out / "worksheets").mkdir(parents=True)
    (out / "style.css").write_text(STYLE, encoding="utf-8")

    set_nav_chains(chapters, worksheets)
    for page in chapters + worksheets:
        target = out / page.out_dir / page.filename
        target.write_text(build_chapter_page(page), encoding="utf-8")

    (out / "index.html").write_text(build_index(chapters, worksheets), encoding="utf-8")
    (out / "worksheets" / "index.html").write_text(
        build_worksheets_index(worksheets), encoding="utf-8"
    )

    problems.extend(validate_site_links(out))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the first-year guide static site.")
    parser.add_argument("--out", default=None, help="output directory (default: site/)")
    parser.add_argument("--check-only", action="store_true", help="validate sources, write nothing")
    args = parser.parse_args(argv)

    problems = build(out_dir=args.out, check_only=args.check_only)
    if args.check_only:
        if problems:
            print("Source checks FAILED:")
            for p in problems:
                print("  -", p)
            return 1
        print("Source checks passed.")
        return 0

    if problems:
        print("Build completed, but validation found problems:")
        for p in problems:
            print("  -", p)
        return 1

    out = Path(args.out or DEFAULT_OUT)
    pages = len(list(out.rglob("*.html")))
    print(f"Build OK: {pages} HTML pages in {out}")
    print("Local-first: open site/index.html in any browser. No network required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
