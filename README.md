# New Nurse: The First-Year Survival Guide

An education-only manual for surviving — and actually enjoying — the first year of nursing. Plain English, step by step, never condescending: the way a friend would explain it.

**Education only — not medical advice.** This guide teaches habits, checklists, and self-management. It does not teach clinical care and never overrides your facility's policies, your state practice act, or your clinical team. When in doubt, the policy manual and your escalation chain come first.

Built by [Asdale Dynamics, LLC](https://dylanasdale.github.io) — beginner-friendly AI education, books, and practical tools, published local-first.

## What is inside

| Chapter | One-liner |
|---|---|
| 00 · Read this first | How to use the guide + the disclaimers that matter |
| 01 · Orientation expectations | What orientation is actually for, and what "done" looks like |
| 02 · Asking questions | Scripts for asking without feeling dumb |
| 03 · Organizing report notes | A report sheet that survives all twelve hours |
| 04 · Preceptors and feedback | Feedback as fuel: the bar, the gap, the stretch |
| 05 · Night-shift survival | Sleep blocks, caffeine leases, drive-home plans |
| 06 · Confidence math | The 100-shifts-to-comfort model, tracked honestly |
| 07 · Burnout early-warning signs | Amber lights, caught while they are still cheap |
| 08 · When to switch units | Hard stretch versus wrong fit — a sorting tool |
| 09 · Glossary | The words they will use on day one, translated |
| Worksheets (5) | Shift worksheet, night-shift plan, 100-shift confidence log, weekly burnout check, feedback notes |

## Run it (local-first, offline)

No dependencies. Python 3.10+ standard library only.

```bash
python3 build.py            # builds the static site into site/ and validates links
python3 build.py --check-only   # validate sources without writing anything
python3 -m unittest discover -s tests -v   # run the test suite
```

Then open `site/index.html` in any browser. No server, no network, no accounts, no analytics — nothing leaves your machine. Worksheets are print-styled, so `Ctrl/Cmd+P` gives clean printable pages.

## Project layout

```
build.py        stdlib-only static site generator (markdown -> HTML) + validation
docs/           the manual, chapter by chapter (markdown)
worksheets/     printable worksheets and logs (markdown)
tests/          unittest suite for the renderer, build, and repo integrity
site/           generated output (gitignored; rebuild anytime)
```

## Related projects

This guide complements its sibling tools:

- **nclex-style-quiz-trainer** — practice-style quizzes for license-exam study and knowledge refresh.
- **sbar-report-builder-webapp** — builds SBAR handoff reports in a form; pairs naturally with chapter 3.

## Privacy and safety

- Local-first: the build and the site make zero network requests (enforced by a strict Content-Security-Policy in every generated page).
- No secrets, no API keys, no patient data, no personal data — the worksheets are blank by design, and a test suite checks for accidental credentials.
- Education-only framing is asserted on every page, in every chapter, and in every worksheet.

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Asdale Dynamics, LLC.
