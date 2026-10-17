# Dogfood build: Klinik Gigi Senyum Sehat

Date: 2026-10-17 · Mode: auto · Site type: company-profile · Brief and directions in
`examples/klinik-senyum-sehat/`

One real build, done by following `skills/web-build/SKILL.md` step by step, to test the
heuristics outside the stubbed tests.

**Prompt:** "buat company profile Klinik Gigi Senyum Sehat di Surabaya, untuk keluarga
muda, pasien bisa booking lewat WhatsApp".

## What happened

- Direction procedure: anchors (keluarga muda, Surabaya, klinik gigi + WhatsApp), formality
  filter (health: formal or neutral only), three styles across five directions, spread
  0.36 / 0.22 / 0.20 / 0.14 / 0.08, layouts the brief can fill. The sampler drew dir-1
  (clean-swiss, sage-clinic); no layout warnings.
- Check: round 1 had one error, round 2 had zero errors and zero warnings, constraint score
  100%. Phone (360 px) and desktop render without horizontal scroll.
- Handoff: nine placeholders on the site, each with its pages.

## Found and fixed

| Finding | Effect | Fix |
| --- | --- | --- |
| `tokens.json` named small sizes `step--1`; `tokens.css` named them `step-neg-1` | `context` advertised variables that did not exist and that stylelint rejects | one naming function for both; test that every advertised token exists in `tokens.css` |
| `base.css` set links to `inherit` and the focus ring to the accent | the new readable `--pd-color-link` went unused; faint accents gave a focus ring under 3:1 | links and focus ring use `--pd-color-link` |
| `compile_tokens` always said "run scaffold.py" | after a token change the next step was refused | it copies `tokens.css` into an existing site and says "run check.py" |
| Handoff listed placeholders from `gaps.json` | asked for facts the site never shows; missed placeholders the pages do show, including the WhatsApp link | placeholders are scanned from the built pages, with the pages they appear on; unused facts listed separately (also in `EXPLAIN.html`) |
| Agent wrote its own placeholder wording | handoff and page lists drift apart | step 6 rule: reuse the placeholder text `context` prints |
| Header and footer ran to the screen edges, content was centred | edges did not line up on desktop | conventions rule: header, main, and footer share one container width |

## Still open

- Browsers request `/favicon.ico`; the scaffold creates none, so every page load logs one
  404 until the client adds an icon.
- `context` lists every placeholder of the project on every page, not only the page's own.
- The semantic accessibility review (subagent with `a11y-judge.md`) was done by the same
  agent here; an independent subagent would be stronger.
