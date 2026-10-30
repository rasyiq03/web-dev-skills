---
name: web-build
description: Build a complete website from a short prompt - company profile, landing page, portfolio, small-business product catalog, or dashboard, in Indonesian, English, or both. Use whenever the user asks to make, generate, restyle, or redesign a website or web page (for example "buatkan website", "bikin landing page").
---

# web-build

Turn one prompt into a finished site in its own project folder. Decisions come first, code
second, checks last. Scripts do every deterministic step; you write only the files marked
"you" below and fix what the checks report.

**Two folders.** `<project>` is the website and nothing else (`index.html`, `pages/`,
`css/`, `js/`, `data/`, `assets/`). `<work>` is `<project>/.ScaffolDev/` and holds every
other file ScaffolDev reads or writes: brief, decisions, copy, graph, trace, reports,
`HANDOFF.md`, `EXPLAIN.html`. Deleting `<work>` leaves a clean site. Never put a ScaffolDev
file in `<project>`, and never make a site file depend on `<work>`.

## At a glance

| Step | You | Script (`run …`) | Result |
| --- | --- | --- | --- |
| 1 Brief | write `<work>/brief.yaml` | `path`, `validate_brief` | `<work>/brief.yaml` |
| 2 Gaps | relay the URL (interactive only) | `gaps`, `serve` | `<work>/gaps.json` |
| 3 Direction | write `<work>/directions.yaml` | `pick_direction` | `<work>/decisions.yaml` |
| 4 Scaffold | nothing | `compile_tokens`, `scaffold` | site skeleton in `<project>` |
| 5 Copy | write copy and mock data | none | `<work>/content/<lang>.yaml` |
| 6 Build | fill each page | `context` | finished site in `<project>` |
| 7 Check | fix findings | `check` | `<work>/report.json` |
| 8 Handoff | show the summary | `handoff` | `<work>/HANDOFF.md`, `<work>/EXPLAIN.html` |

## Modes

- **auto** (default): work through the steps without stopping.
- **guided**: the user wants to learn or be guided ("mode terpandu", "ajari aku"). Read
  `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/mode-guided.md` and follow it in every
  step.
- **deep**: the user wants one prompt in and a ready site out ("deep work", "mode
  musyawarah", "langsung jadi"). Read
  `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/mode-deep.md`: a council of AI roles
  decides at four sittings. It costs more, so use it only when asked.

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
  printed questions, update `<work>/brief.yaml`, run again. `4` the interactive form timed out.
- **First run on a machine** (usually `validate_brief`) installs Python packages and Node
  tools once. It needs internet and can take several minutes: give it a 10-minute timeout
  and do not interrupt or repeat it.

## Ground rules

- Go through the steps in order. Write site files only after step 4 succeeds.
- Use only facts the user gave. Every other fact (address, phone, prices, hours,
  testimonials, client logos, statistics) becomes a placeholder `[[ISI: <what>]]`.
- `<project>` and `<work>` are the folders printed in step 1 (`PROJECT:` and `WORK:`).
- When the brief's languages include `id` or the business is in Indonesia, read
  `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/indonesia.md` once and follow it in
  steps 3 to 6 and whenever you talk to the user.
- Talk to the user in their language, in short, plain sentences.
- Work without stopping to ask, unless the user asked for interactive mode (then set
  `interactive: true` in the brief) or guided mode, or a script exits with `3`.

## Steps

1. **Brief.** Pick a short kebab-case slug and run `run path <slug>`; it prints
   `PROJECT:` (`<project>`) and `WORK:` (`<work>`). Write `<work>/brief.yaml` following
   `${CLAUDE_PLUGIN_ROOT}/skills/web-build/schemas/brief.schema.json`: fields the prompt
   states get `source: stated`, every other field is `unknown`. Run
   `run validate_brief <slug>` until it passes.

2. **Gaps.** Run `run gaps <slug>`. It turns missing facts into placeholders and lists the
   open design decisions in `<work>/gaps.json`. Interactive mode only: start `run serve <slug>` in
   the background, give the user the printed URL, and wait for the script to report the
   answers.

3. **Direction.** Follow `${CLAUDE_PLUGIN_ROOT}/skills/web-design/SKILL.md` to write
   `<work>/directions.yaml`, then run `run pick_direction <slug>`. It writes
   `<work>/decisions.yaml`.

4. **Tokens and scaffold.** Run `run compile_tokens <slug>`, then `run scaffold <slug>`.
   This creates the site in `<project>`: the folders, `css/tokens.css`, `css/base.css`, and
   one skeleton HTML file per page with empty section shells in the right order.

5. **Copy.** Read `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/copy-<lang>.md` for each
   language in the brief, and
   `${CLAUDE_PLUGIN_ROOT}/skills/web-build/site-types/<site_type>.yaml`. Write
   `<work>/content/<lang>.yaml` with one entry per section of the site type: headings, body
   text, button labels.
   - Collections the brief gives (a product list, projects) are content: write them in.
   - Collections it lacks, and every dashboard figure, are data: one endpoint each in
     `<project>/js/api/endpoints.js` plus its response in `<project>/data/mock/<name>.mock.json`
     (see "Data and the mock API" in the conventions below).
   - A stated API source means `API_MODE = 'live'` with that API's paths.

6. **Build.** Read `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/conventions.md` once
   (for a dashboard also `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/dashboard.md`).
   Then, one page at a time, run `run context <slug> <page>`; it prints exactly what that
   page needs (decisions, section patterns, token names, component recipes, this page's
   placeholders and the rest of the site's, and `risk` lines for sections whose facts are
   missing). Fill each section shell from
   `<work>/content/<lang>.yaml`, keeping its `class`, `id`, and `data-pd-pattern`. Write CSS
   and JS in the files the scaffold made, using only the variables in `css/tokens.css`.
   - Build `index` first and completely; the other pages reuse its header, footer, and
     components instead of restyling them.
   - Write the style's components once in `css/components.css` (button, card, label), then
     compose sections from them. A second variant of the same thing is a modifier, not a
     new class.
   - Work at 360 px first, then add wider layouts with `min-width` media queries.
   - A `risk` section gets a labelled placeholder of the real content's size, so the page
     does not collapse when the client fills it in.
   - Use placeholder texts exactly as `context` prints them, so the handoff list matches the
     page; a WhatsApp button is `href="https://wa.me/[[ISI: nomor WhatsApp]]"`. Write a new
     placeholder only for something no listed fact covers.

7. **Check and fix.** Run `run check <slug>`. It formats the code, runs the linters and the
   audit, and writes `<work>/report.json` with each finding and a suggested fix (file paths
   are relative to `<project>`). Fix every `error`,
   then every `warning`, and run it again; the script counts rounds and says when to stop.
   Fix in this order, because each kind can cause the next:
   - `tool-failed` first: nothing else in the report is reliable until every tool ran.
   - Contrast or token findings: change the decision with `run decide`, never override a
     color in page CSS.
   - Rules that repeat across files: fix the shared component or the cause once, not each
     occurrence.
   - Then HTML structure, then CSS and JS style, then the design and copy audit.
   If you can start a subagent, give it
   `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/a11y-judge.md` and the built pages, and
   apply its findings as one extra round. Save its answer as `<work>/a11y-review.json`:
   `{"reviewer": "subagent", "pages": [<its objects>]}` (`"self"` if you reviewed without a
   subagent), and add `"applied": "<what you changed>"` to each finding you fixed. Without
   that file the handoff reports the review as skipped.

8. **Handoff.** Run `run handoff <slug>` and show its summary to the user exactly as
   printed: assumptions taken, placeholders to fill, and check scores. It also writes
   `<work>/EXPLAIN.html`; tell the user it opens with a double-click, needs no internet, and shows
   who decided what, why, and what a change would touch. `run explain <slug>` rewrites it
   at any step. Section 7 of `HANDOFF.md` lists the learning signals (P1–P6); when the
   dependence risk is high, say so in one plain sentence and point to what lowers it.

## Explaining, changing, and accepting a decision

Every script keeps `<work>/graph.json` up to date: requirements, decisions, tokens,
sections, files, checks, and findings, with how they connect. Node ids look like
`d-palette-1`, `req-audience`, `color.accent`, or `section:index#hero`. Retell every
answer in plain words; do not paste raw output.

- **Why?** `run graph <slug> --why <node>`.
- **What would change?** `run graph <slug> --impact <node>`; tell the user before changing.
- **Change one decision:** `run decide <slug> <decision> --choice <value> --reason "<why>"`
  (layout also takes `--section <id>`, tone may take `--register id=Anda`). It reruns only
  what depends on that decision and says what is left for you; its errors list the valid
  values. The style itself cannot be changed alone: offer another direction instead.
- **Accept a decision** the user confirmed: `run decide <slug> <decision> --accept
  --verification <pick|compare|justify|predict> --reason "<why>"`.
- The reason is the user's, in their words. Ask for it in one sentence; never invent it.
  Use `--by ai` only when you change a decision yourself, for example to fix a check.

## Restyling an existing project

Keep the slug and brief, then repeat steps 3, 4, and 6 to 8. `run scaffold <slug> --force`
deletes the site files in `<project>` (never `<work>` or `.git`), so first copy
`js/api/endpoints.js` and `data/mock/` aside and put them back afterwards; `<work>/content/`
is kept. Projects made before `.ScaffolDev/` existed are moved into this layout
automatically the first time a script opens them.
