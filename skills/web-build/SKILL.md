---
name: web-build
description: Build a complete website from a short prompt - company profile, landing page, portfolio, small-business product catalog, or dashboard, in Indonesian, English, or both. Use whenever the user asks to make, generate, restyle, or redesign a website or web page (for example "buatkan website", "bikin landing page").
---

# web-build

Turn one prompt into a finished site in its own project folder. Decisions come first, code
second, checks last. Scripts do every deterministic step; you write only the files marked
"you" below and fix what the checks report.

## At a glance

| Step | You | Script (`run …`) | Result in `<project>/` |
| --- | --- | --- | --- |
| 1 Brief | write `brief.yaml` | `path`, `validate_brief` | `brief.yaml` |
| 2 Gaps | relay the URL (interactive only) | `gaps`, `serve` | `gaps.json` |
| 3 Direction | write `directions.yaml` | `pick_direction` | `decisions.yaml` |
| 4 Scaffold | nothing | `compile_tokens`, `scaffold` | `site/` skeleton |
| 5 Copy | write copy and mock data | none | `content/<lang>.yaml` |
| 6 Build | fill each page | `context` | finished `site/` |
| 7 Check | fix findings | `check` | `report.json` |
| 8 Handoff | show the summary | `handoff` | summary for the user |

## Running scripts

Every script runs through one command, from the folder Claude Code was opened in:

`python "${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py" <script> <slug>`

In this file `run <script> <slug>` is short for that command. Always type the full command.
If `${CLAUDE_PLUGIN_ROOT}` appears literally in this file (the skill was loaded without
plugin support), it means the folder that contains `skills/`.

- **Read the last line.** Each script ends with `NEXT: <what to do>`. "run gaps.py" there
  means `run gaps <slug>`.
- **Exit codes.** `0` done. `1` bad or missing input: fix what the message names, run again.
  `2` the check found problems: go on with step 7. `3` facts are missing: ask the user the
  printed questions, update `brief.yaml`, run again. `4` the interactive form timed out.
- **First run on a machine** (usually `validate_brief`) installs Python packages and Node
  tools once. It needs internet and can take several minutes: give it a 10-minute timeout
  and do not interrupt or repeat it.

## Ground rules

- Go through the steps in order. Write site files only after step 4 succeeds.
- Use only facts the user gave. Every other fact (address, phone, prices, hours,
  testimonials, client logos, statistics) becomes a placeholder `[[ISI: <what>]]`.
- `<project>` is the folder printed in step 1. Write every project file there.
- Work without stopping to ask, unless the user asked for interactive mode (then set
  `interactive: true` in the brief) or a script exits with `3`.

## Steps

1. **Brief.** Pick a short kebab-case slug and run `run path <slug>`; it prints
   `PROJECT: <folder>`, which is `<project>`. Write `<project>/brief.yaml` following
   `${CLAUDE_PLUGIN_ROOT}/skills/web-build/schemas/brief.schema.json`: fields the prompt
   states get `source: stated`, every other field is `unknown`. Run
   `run validate_brief <slug>` until it passes.

2. **Gaps.** Run `run gaps <slug>`. It turns missing facts into placeholders and lists the
   open design decisions in `gaps.json`. Interactive mode only: start `run serve <slug>` in
   the background, give the user the printed URL, and wait for the script to report the
   answers.

3. **Direction.** Follow `${CLAUDE_PLUGIN_ROOT}/skills/web-design/SKILL.md` to write
   `directions.yaml`, then run `run pick_direction <slug>`. It writes `decisions.yaml`.

4. **Tokens and scaffold.** Run `run compile_tokens <slug>`, then `run scaffold <slug>`.
   This creates `site/`: the folders, `css/tokens.css`, `css/base.css`, and one skeleton
   HTML file per page with empty section shells in the right order.

5. **Copy.** Read `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/copy-<lang>.md` for each
   language in the brief, and
   `${CLAUDE_PLUGIN_ROOT}/skills/web-build/site-types/<site_type>.yaml`. Write
   `content/<lang>.yaml` with one entry per section of the site type: headings, body text,
   button labels.
   - Collections the brief gives (a product list, projects) are content: write them in.
   - Collections it lacks, and every dashboard figure, are data: one endpoint each in
     `site/js/api/endpoints.js` plus its response in `site/data/mock/<name>.mock.json`
     (see "Data and the mock API" in the conventions below).
   - A stated API source means `API_MODE = 'live'` with that API's paths.

6. **Build.** Read `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/conventions.md` once.
   Then, one page at a time, run `run context <slug> <page>`; it prints exactly what that
   page needs (decisions, section patterns, token names, component recipes, placeholders).
   Fill each section shell from `content/<lang>.yaml`, keeping its `class`, `id`, and
   `data-pd-pattern`. Write CSS and JS in the files the scaffold made, using only the
   variables in `css/tokens.css`.

7. **Check and fix.** Run `run check <slug>`. It formats the code, runs the linters and the
   audit, and writes `report.json` with each finding and a suggested fix. Fix every `error`,
   then every `warning`, and run it again; the script counts rounds and says when to stop.
   If you can start a subagent, give it
   `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/a11y-judge.md` and the built HTML, and
   apply its findings as one extra round. Otherwise note "semantic review skipped".

8. **Handoff.** Run `run handoff <slug>` and show its summary to the user exactly as
   printed: assumptions taken, placeholders to fill, and check scores.

## Restyling an existing project

Keep the slug and brief, then repeat steps 3, 4, and 6 to 8. `run scaffold <slug> --force`
deletes `site/`, so first copy `site/js/api/endpoints.js` and `site/data/mock/` aside and put
them back afterwards; `content/` is kept.
