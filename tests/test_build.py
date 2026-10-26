#!/usr/bin/env python3
"""Tests for the New Nurse First-Year Guide.

Runs the build into a temporary directory and verifies:
  * the markdown renderer handles every construct used by the docs
  * the site builds, links resolve, and disclaimers land on every page
  * repo integrity: LICENSE line, README credit, no secrets, deterministic builds

Run with:  python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import hashlib
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402


def build_to_temp() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="nn-guide-test-"))
    problems = build.build(out_dir=tmp)
    assert not problems, f"build reported problems: {problems}"
    return tmp


class MarkdownRendererTests(unittest.TestCase):
    def render(self, text: str) -> str:
        return build.render_markdown(text)

    def test_bold_italic_code(self):
        html = self.render("**bold** and *calm* and `tick()`")
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<em>calm</em>", html)
        self.assertIn("<code>tick()</code>", html)

    def test_link_with_resolver(self):
        html = build.render_markdown(
            "see [the chapter](../docs/06-confidence-math.html)",
            resolver=lambda t: "../chapters/06-confidence-math.html",
        )
        self.assertIn('href="../chapters/06-confidence-math.html"', html)
        self.assertIn(">the chapter</a>", html)

    def test_external_link_untouched(self):
        html = self.render("[hub](https://example.com)")
        self.assertIn('href="https://example.com"', html)

    def test_table(self):
        html = self.render("| a | b |\n|---|---|\n| 1 | 2 |")
        self.assertIn("<table>", html)
        self.assertIn("<th>a</th>", html)
        self.assertIn("<td>2</td>", html)

    def test_fenced_code_escapes_html(self):
        html = self.render("```\n<a> & 'quote'\n```")
        self.assertIn("<pre><code>", html)
        self.assertIn("&lt;a&gt; &amp; 'quote'", html)
        self.assertNotIn("<pre><code><a>", html)

    def test_unordered_nested_in_ordered(self):
        html = self.render("1. Top\n   - child\n2. Next")
        self.assertIn("<ol><li>Top<ul><li>child</li></ul></li><li>Next</li></ol>", html)

    def test_checkbox_item(self):
        html = self.render("- [ ] protect sleep\n- [x] done thing")
        self.assertIn("☐", html)
        self.assertIn("☑", html)

    def test_blockquote(self):
        html = self.render("> quoted advice here")
        self.assertIn("<blockquote><p>quoted advice here</p></blockquote>", html)

    def test_hr_and_headings(self):
        html = self.render("# Title\n\n## Sub\n\ntext\n\n---\n")
        self.assertIn("<h1>Title</h1>", html)
        self.assertIn("<h2>Sub</h2>", html)
        self.assertIn("<hr>", html)

    def test_html_is_escaped_outside_code(self):
        html = self.render("a < b & c > d")
        self.assertIn("a &lt; b &amp; c &gt; d", html)
        self.assertNotIn("< b", html.replace("&lt;", ""))


class BuildOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = build_to_temp()

    def test_expected_files_exist(self):
        for rel in (
            "index.html",
            "style.css",
            "chapters/00-read-me-first.html",
            "chapters/09-glossary.html",
            "worksheets/index.html",
            "worksheets/shift-worksheet.html",
            "worksheets/night-shift-worksheet.html",
            "worksheets/confidence-log.html",
            "worksheets/burnout-check.html",
            "worksheets/feedback-notes.html",
        ):
            self.assertTrue((self.site / rel).exists(), f"missing {rel}")

    def test_index_lists_every_chapter(self):
        index = (self.site / "index.html").read_text(encoding="utf-8")
        for page in build.collect_pages()[0]:
            self.assertIn(page.title, index, f"index missing {page.title}")

    def test_every_page_has_banner_and_footer(self):
        for html_file in self.site.rglob("*.html"):
            text = html_file.read_text(encoding="utf-8")
            self.assertIn(build.BANNER_TEXT, text, str(html_file))
            self.assertIn("Copyright (c) 2026 Asdale Dynamics, LLC", text, str(html_file))
            self.assertIn("not medical advice", text, str(html_file))

    def test_csp_is_offline_first(self):
        index = (self.site / "index.html").read_text(encoding="utf-8")
        self.assertIn("Content-Security-Policy", index)
        self.assertIn("default-src 'none'", index)

    def test_no_external_resource_requests(self):
        # education-only, local-first: no <script>, no external <img>/<link>
        for html_file in self.site.rglob("*.html"):
            text = html_file.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"<script", str(html_file))
            self.assertNotRegex(text, r'<img[^>]+src="http', str(html_file))
            self.assertNotRegex(text, r'<link[^>]+href="http', str(html_file))

    def test_nav_chain_prev_next(self):
        ch2 = (self.site / "chapters/02-asking-questions.html").read_text(encoding="utf-8")
        self.assertIn("01-orientation-expectations.html", ch2)
        self.assertIn("03-organizing-report-notes.html", ch2)

    def test_link_validation_clean(self):
        self.assertEqual(build.validate_site_links(self.site), [])


class SourceAndRepoIntegrityTests(unittest.TestCase):
    def test_every_source_has_disclaimer(self):
        for src in sorted(list(build.DOCS_DIR.glob("*.md")) + list(build.WORKSHEETS_DIR.glob("*.md"))):
            text = src.read_text(encoding="utf-8")
            self.assertIn("Education only", text, str(src))
            self.assertIn("not medical advice", text, str(src))

    def test_expected_source_counts(self):
        chapters, worksheets = build.collect_pages()
        self.assertGreaterEqual(len(chapters), 9)
        self.assertGreaterEqual(len(worksheets), 5)

    def test_license_exact_copyright_line(self):
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Copyright (c) 2026 Asdale Dynamics, LLC", text)
        self.assertIn("MIT License", text)

    def test_readme_credits_and_instructions(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Asdale Dynamics, LLC", text)
        self.assertIn("not medical advice", text)
        self.assertIn("python3 build.py", text)
        self.assertIn("unittest", text)
        self.assertIn("nclex-style-quiz-trainer", text)
        self.assertIn("sbar-report-builder-webapp", text)

    def test_no_secrets_or_credentials(self):
        patterns = [
            r"(?i)\b(api[_-]?key|apikey|secret|passwd|password|access[_-]?token)\b\s*[:=]",
            r"sk-[A-Za-z0-9]{16,}",
            r"gh[pousr]_[A-Za-z0-9]{20,}",
            r"AKIA[0-9A-Z]{16}",
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN-shaped personal data
        ]
        targets = [
            p for p in ROOT.rglob("*")
            if p.is_file()
            and "site" not in p.relative_to(ROOT).parts
            and "__pycache__" not in p.parts
            and p.name != "LICENSE"
        ]
        for path in targets:
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            for pattern in patterns:
                self.assertNotRegex(
                    text, pattern, f"{path.relative_to(ROOT)} matches secret pattern {pattern}"
                )

    def test_build_is_deterministic(self):
        def digest(tree: Path) -> str:
            sha = hashlib.sha256()
            for f in sorted(tree.rglob("*")):
                if f.is_file():
                    sha.update(str(f.relative_to(tree)).encode())
                    sha.update(f.read_bytes())
            return sha.hexdigest()

        with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
            self.assertEqual(build.build(Path(t1)), [])
            self.assertEqual(build.build(Path(t2)), [])
            self.assertEqual(digest(Path(t1)), digest(Path(t2)))


class CheckOnlyModeTests(unittest.TestCase):
    def test_check_only_validates_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            problems = build.build(out_dir=Path(tmp), check_only=True)
            self.assertEqual(problems, [])
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_check_only_flags_missing_disclaimer(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = build.DOCS_DIR
            backup = (src / "00-read-me-first.md").read_text(encoding="utf-8")
            try:
                scrubbed = backup.replace("Education only", "General reference")
                scrubbed = scrubbed.replace("not medical advice", "not clinical guidance")
                (src / "00-read-me-first.md").write_text(scrubbed, encoding="utf-8")
                problems = build.build(out_dir=Path(tmp), check_only=True)
                self.assertTrue(any("disclaimer" in p for p in problems))
            finally:
                (src / "00-read-me-first.md").write_text(backup, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
