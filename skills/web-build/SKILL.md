---
name: web-build
description: Build a complete website from a short prompt - company profile, landing page, portfolio, small-business product catalog, or dashboard, in Indonesian, English, or both. Use whenever the user asks to make, generate, or redesign a website or web page.
---

# web-build

Turn one prompt into a finished site in `projects/<slug>/`. Decisions come first, code
second, checks last. Scripts do every deterministic step; you do only steps 1, 3, 5, 6
and the fixes in step 7.

## Ground rules

- Work through the steps in order. Write site files only after step 4 succeeds.
- Use only facts the user gave. Every other fact (address, phone, prices, hours,
  testimonials, client logos, statistics) becomes a placeholder `[[ISI: <what>]]`.
- Run commands from the repository root. Every script prints what it wrote and exits
  non-zero on failure; read its output before moving on.
- Work without stopping to ask the user, unless they asked for interactive mode or a
  script tells you to ask.

## Steps

1. **Brief.** Choose a short kebab-case slug. Write `projects/<slug>/brief.yaml` following
   `schemas/brief.schema.json`. Set every field the prompt does not state to `unknown`;
   mark stated fields with `source: stated`. Then run:
   `python skills/web-build/scripts/validate_brief.py <slug>` and fix until it passes.

2. **Gaps.** Run `python skills/web-build/scripts/gaps.py <slug>`. It turns missing facts
   into placeholders and lists the open design decisions in `gaps.json`.
   Interactive mode only: run `python skills/web-build/scripts/serve.py <slug>` in the
   background, give the user the printed URL, and wait until the script reports the answers.

3. **Direction.** Read `skills/web-design/SKILL.md` and follow it to write
   `projects/<slug>/directions.yaml`. Then run
   `python skills/web-build/scripts/pick_direction.py <slug>`.
   It writes `decisions.yaml`.

4. **Tokens and scaffold.** Run `python skills/web-build/scripts/compile_tokens.py <slug>`,
   then `python skills/web-build/scripts/scaffold.py <slug>`. The scaffold creates
   `projects/<slug>/site/`: the folder structure, `css/tokens.css`, `css/base.css`, and one
   skeleton HTML file per page whose sections are empty shells in the right order.

5. **Copy.** Read `references/copy-<lang>.md` for each language in the brief and
   `site-types/<site_type>.yaml`. Write `projects/<slug>/content/<lang>.yaml`: one entry per
   section listed in the site type, with headings, body text, and button labels.
   Collections the brief does not give (catalog products, portfolio projects) and every
   dashboard figure are data, not copy: add one endpoint per collection to
   `site/js/api/endpoints.js` and its response to `site/data/mock/<name>.mock.json`,
   following "Data and the mock API" in `references/conventions.md`. Collections the brief
   does give are content and go straight into the page; a stated API source means
   `API_MODE = 'live'` with that API's paths.

6. **Build.** Read `references/conventions.md`. Then, one page at a time, run
   `python skills/web-build/scripts/context.py <slug> <page>`; it prints exactly what that
   page needs (decisions, section patterns, token names, component recipes, placeholders).
   Fill each section shell of the page from `content/<lang>.yaml`, keeping its `class`,
   `id`, and `data-pd-pattern`, and write the CSS and JS in the files the scaffold made,
   using only the variables in `css/tokens.css`.

7. **Check and fix.** Run `python skills/web-build/scripts/check.py <slug>`. It formats the
   code, runs the linters and the audit, and writes `report.json` with each finding and a
   suggested replacement. Fix every `error`, then every `warning`, then run it again.
   The script counts rounds, keeps a copy of each round, and tells you when to stop.
   If you can start a subagent, give it `references/a11y-judge.md` and the built HTML, and
   apply its findings as one extra round. If you cannot, note "semantic review skipped".

8. **Handoff.** Run `python skills/web-build/scripts/handoff.py <slug>` and show its summary
   to the user exactly as printed: assumptions taken, placeholders to fill, and check scores.
