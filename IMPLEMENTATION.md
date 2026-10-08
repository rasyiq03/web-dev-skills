# IMPLEMENTATION.md — build brief for Claude Code

This package already contains every instruction file, schema, data file, and lint config.
What is missing is the scripts. This file specifies each script precisely enough to build
and test it. Build milestone by milestone; do not start a milestone before the previous
gate passes.

Hand it to Claude Code with: *"Read IMPLEMENTATION.md and build milestone v0.1. Run the
gate tests at the end and show me the results."*

---

## 0. Ground rules for the implementation

- **Python 3.11+**, dependencies only from `requirements.txt`. `serve.py` uses the standard
  library only. Node tools come from `npm run setup`.
- Every script: `python skills/web-build/scripts/<name>.py <slug> [options]`, run from the
  repository root, reads and writes only inside `projects/<slug>/` (plus reading `skills/`,
  `audit/`, `config/`).
- Exit codes: `0` success · `1` invalid input (message says what to fix) · `2` a check
  failed · `3` the agent must ask the user (message contains the question) · `4` timeout.
- Every script prints a short human-readable summary ending with one line that starts with
  `NEXT:` telling the agent what to do. The agent reads this line; keep it exact.
- Scripts are deterministic: same inputs and seed give byte-identical outputs.
- **Code style of the scripts themselves** follows the house convention: file header and
  section banners in comments, a docstring with I.S. and F.S. for every function, comments
  in Indonesian, names in English. Python formatting: `ruff format` defaults are fine.
- Shared helpers go in `skills/web-build/scripts/lib/` (`paths.py`, `io.py` for YAML/JSON,
  `color.py` for contrast and CIELCh, `report.py`).
- Tests in `tests/` with pytest; fixtures from `examples/kopi-senja/`.

## 1. Final repository layout

```
AGENTS.md  IMPLEMENTATION.md  requirements.txt  package.json
config/          .prettierrc.json .prettierignore eslint.config.js .stylelintrc.json
                 .htmlvalidate.json .editorconfig
audit/           anti-slop.yaml cliches-id.txt cliches-en.txt
skills/
	web-build/
		SKILL.md
		references/  conventions.md copy-id.md copy-en.md a11y-judge.md
		schemas/     brief.schema.json directions.schema.json decisions.schema.json mock.schema.json
		templates/   js/api/ config.js client.js endpoints.js mock-label.js
		site-types/  company-profile.yaml dashboard.yaml landing.yaml portfolio.yaml umkm-catalog.yaml
		scripts/     validate_brief.py gaps.py serve.py pick_direction.py compile_tokens.py
		             scaffold.py context.py check.py handoff.py lib/
	web-design/
		SKILL.md
		styles/      index.yaml neobrutalism.yaml editorial.yaml _template.yaml
		layouts/     patterns.yaml
tools/           sync_adapters.py (v0.1) · render_check.py, build_cliches.py, eval/ (v0.3)
                 export_rdf.py, shapes.ttl (v0.4)
examples/kopi-senja/   brief.yaml directions.yaml decisions.yaml
tests/
projects/<slug>/       created at run time (see section 2)
```

Do not create a `CLAUDE.md`. Claude Code (2.1.277+) reads `AGENTS.md` when no `CLAUDE.md`
exists; if both exist Claude Code follows `CLAUDE.md` and Codex follows `AGENTS.md`, and the
two drift apart. `sync_adapters.py` warns when it finds one.

## 2. Files inside `projects/<slug>/`

| File | Written by | Purpose |
| --- | --- | --- |
| `brief.yaml` | agent (step 1), `serve.py` | Facts and requirements; schema `brief.schema.json` |
| `gaps.json` | `gaps.py` | Requirement ids, placeholders, open decisions, questions |
| `directions.yaml` | agent (step 3) | Five directions; schema `directions.schema.json` |
| `decisions.yaml` | `pick_direction.py` | Chosen decisions and constraints; schema `decisions.schema.json` |
| `tokens.json`, `tokens.css`, `fonts.html` | `compile_tokens.py` | DTCG tokens, CSS variables, Google Fonts link |
| `content/<lang>.yaml` | agent (step 5) | Copy per page and section |
| `site/` | `scaffold.py`, agent | The website |
| `.prettierrc.json` … | `scaffold.py` | Copies of `config/`, hashed in `state.yaml` |
| `report.json`, `rounds/<n>/` | `check.py` | Findings and per-round snapshots |
| `provenance.json`, `HANDOFF.md` | `handoff.py` | File hashes and the summary for the client |
| `state.yaml` | every script | Current step, round counters, seed, config hashes |

### Requirement ids

Every `brief.yaml` field whose `source` is `stated` or `inferred` becomes a requirement with
id `req-<dotted path>`, for example `req-audience`, `req-business.location`,
`req-facts.whatsapp`. These ids are the only valid values in `based_on`.

### `content/<lang>.yaml`

```yaml
pages:
  index:
    title: Kopi Senja — kedai kopi di Bandung
    description: Meta description, at most 155 characters.
    sections:
      hero:
        heading: Kopi Senja
        body: [Satu atau dua kalimat.]
        actions: [{ label: Pesan lewat WhatsApp, href: "[[ISI: tautan WhatsApp]]" }]
      services:
        heading: Menu
        items: [{ name: Kopi susu gula aren, price: "[[ISI: harga]]", note: "" }]
```

Validate it with a small schema in `check.py`: every page and section from the site type is
present; every `href` is a URL, an anchor, a `tel:`/`mailto:`/`https://wa.me/` link, or a
placeholder.

## 3. Script specifications

### 3.1 `validate_brief.py <slug>` (v0.1)

- Validates `brief.yaml` against `brief.schema.json`; prints each error with its path.
- Checks `slug` equals the folder name.
- Loads `site-types/<site_type>.yaml`; for each `required_fields` path whose `source` is
  `unknown`, exits **3** and prints the matching question from `questions` in the brief's
  first language (fallback: a generic "Mohon isi: <field>").
- On success prints the requirement ids and `NEXT: run gaps.py`.

**Accept:** the kopi-senja brief passes; a brief with `business.location: unknown` exits 3
and prints a question; a brief with `source: stated, value: unknown` exits 1.

### 3.2 `gaps.py <slug>` (v0.1)

- `requirements`: list of `{id, path, value, source}` for stated and inferred fields.
- `placeholders`: for each fact listed in the site type that is missing or `unknown`, a
  placeholder string `[[ISI: <label>]]`. Labels come from a dictionary in
  `lib/labels.py` (Indonesian and English labels for the facts used in the four site types;
  fallback: the fact name with underscores replaced by spaces).
- `open_decisions`: `goal`, `tone`, `style_request`, `brand.*` fields that are `unknown`.
- `questions`: the site-type questions whose `field` is still unknown, in file order (the
  files put the most discriminating question first; keep at most 6).
- Writes `gaps.json`; prints counts and `NEXT: write directions.yaml (web-design skill)`,
  or `NEXT: run serve.py` when `brief.interactive` is true.

**Accept:** kopi-senja yields placeholders for address, whatsapp, email, hours, services,
founded_year, client_names, team_members, and requirement ids including
`req-business.cultural_context`.

### 3.3 `serve.py <slug> [--timeout 1800]` (v0.2)

Standard library only (`http.server`, `secrets`, `json`, `threading`).

- Binds `127.0.0.1` on port `0`; prints `URL: http://127.0.0.1:<port>/<token>/` and flushes
  immediately, so it works when the agent runs it in the background, over SSH, or in WSL.
- `token = secrets.token_urlsafe(16)`. Any path without the token → 404. Rejects requests
  whose `Host` header is not `127.0.0.1:<port>` or `localhost:<port>`.
- `GET /<token>/` serves one HTML form built from `gaps.json` questions in the brief's
  language. The page itself follows `conventions.md` (pd- classes, file header, banners).
- `POST /<token>/submit` accepts only `Content-Type: application/json`; the answers travel
  in the body, never in headers or the query string. One submission only; a second → 409.
- Writes answers into `brief.yaml` with `source: stated` and `note: form`, re-runs the
  validation, prints `ANSWERS SAVED` and `NEXT: run gaps.py`, and exits 0.
- No submission before the timeout → prints `NEXT: continue without answers` and exits 4.

**Accept:** pytest drives it with `urllib`: wrong token 404, wrong Host 403, double submit
409, timeout exit 4 (use `--timeout 2`).

### 3.4 `pick_direction.py <slug> [--seed N] [--pick dir-K]` (v0.1)

1. Validate `directions.yaml` against `directions.schema.json`.
2. Cross-check: probabilities sum to 1 ± 0.01; `style` exists in `styles/index.yaml`;
   `palette` and `type_pairing` exist in that style file or are `custom`; every `layout`
   key is a section id of the site type and every value is a pattern id of that section's
   `pattern_kind`; every `based_on` id exists in `gaps.json`; each pair of directions
   differs on at least 3 of the 6 axes (style, palette, type_pairing, layout, motion,
   tone); `register` has an entry for each brief language. Any failure → exit 1 with a
   list of what to change.
3. Choose: `--pick` → that direction, `source: client-picked`. Otherwise
   `seed = --seed or secrets.randbits(32)`, then
   `random.Random(seed).choices(directions, weights=probabilities)`, `source: sampled`.
   Store the seed in `decisions.yaml` and `state.yaml`.
4. Generate `decisions.yaml` with exactly these decisions and constraint templates:

| Decision | Choice text | Rationale key | realized_by | Constraints |
| --- | --- | --- | --- | --- |
| `d-style-1` | style id | `style` | `border.strong`, `shadow.hard` | `c-style-border`: token-equals `border.strong` = style's value |
| `d-palette-1` | palette id | `color` | the five `color.*` tokens | `c-palette-paper`: token-equals `color.paper`; `c-contrast-body`: contrast-min ink/paper 4.5; `c-contrast-accent`: contrast-min accent-ink/accent 4.5 |
| `d-typo-1` | `<pairing>: <display> / <body> / <mono>` | `typography` | `font.display`, `font.body`, `font.mono` | `c-type-heading`: var-used `h1` font-family `--pd-font-display`; `c-type-body`: var-used `body` font-family `--pd-font-body` |
| `d-layout-1` | `section=pattern, …` in site-type order | `layout` | pattern ids | `c-layout-<section>`: pattern-present `<pattern>` on that section's page (`index.html` or `pages/<page>.html`) |
| `d-motion-1` | `none`/`low`/`medium` | `motion` | `motion.fast`, `motion.base` | `c-motion`: motion-max level |
| `d-tone-1` | `<tone> (<lang>: <pronoun>, …)` | `tone` | — | `c-register-<lang>` per language: register lang pronoun |

   `based_on` of every decision = the direction's `based_on`. Validate the result against
   `decisions.schema.json` before writing.

**Accept:** `--pick dir-2` on the kopi-senja fixtures reproduces
`examples/kopi-senja/decisions.yaml` exactly, except `seed`. The same `--seed` gives the
same choice on every run. Over 1,000 seeds the choice frequencies match the probabilities
within ±3 percentage points.

### 3.5 `compile_tokens.py <slug>` (v0.1)

- Inputs: `decisions.yaml`, the chosen direction, the style file.
- `tokens.json` in W3C Design Tokens (DTCG) format: groups `color` (ink, paper, accent,
  muted, accent-ink), `font` (display, body, mono, each with a generic fallback), `size`
  (`step--2` … `step-5`, value `base × ratio^n` in rem, 3 decimals), `space`, `radius`,
  `border`, `shadow`, `motion`.
- `tokens.css`: one `:root` block with `--pd-<group>-<name>` for every token, grouped with
  section banners and a file header, following `conventions.md`.
- `fonts.html`: one `<link rel="preconnect">` pair and one Google Fonts `css2` link for the
  three families with the weights the style uses.
- Contrast check: ink/paper, muted/paper, and accent-ink/accent must be ≥ 4.5:1, else exit 2
  naming the pair and its ratio. Use the WCAG 2.x relative-luminance formula in
  `lib/color.py`.
- **Chart and state colors** (always generated; dashboards use them, other sites may):
  derived in OKLCH so they work for custom palettes too. `color.chart-1` is the accent;
  `chart-2` … `chart-6` rotate the accent hue in steps of 60°, keep its chroma (clamped to
  the sRGB gamut), and take the lightness closest to the accent's that reaches ≥ 3:1
  against paper (WCAG 1.4.11, non-text contrast). `color.positive`, `color.negative`, and
  `color.warning` use hues 145°, 25°, and 80° with the lightness that reaches ≥ 4.5:1
  against paper, so they can also color text. Implement OKLCH ↔ sRGB in `lib/color.py`.

**Accept:** for dir-2, `--pd-color-paper: #F4EBDD;`, `--pd-font-display: 'Archivo Black',
sans-serif;` exist; a custom palette with ink `#777777` on paper `#888888` exits 2.

### 3.6 `scaffold.py <slug>` (v0.1)

- Creates the `site/` tree from `conventions.md`; copies `tokens.css` to `site/css/`.
- Writes `site/css/base.css` (reset, element defaults using only token variables, `h1-h3`
  in `--pd-font-display`, `body` in `--pd-font-body`, visible focus outline), and empty
  `layout.css`, `components.css`, `js/main.js`, each with its file header.
- For every page of the site type writes a skeleton HTML: doctype, file header comment,
  `<html lang>` from the first brief language, meta charset and viewport,
  `<meta name="generator" content="pd-web-skills <version>">`, the `fonts.html` links, CSS
  links in order, `<header>`, `<main>`, `<footer>`, and for each section of that page:
  its three-line banner and
  `<section class="pd-section pd-section--<id>" id="<id>" data-pd-pattern="<pattern>"></section>`.
  The agent fills the sections; the shells guarantee order and pattern attributes.
- Copies every file in `config/` into `projects/<slug>/` and stores their SHA-256 in
  `state.yaml`.
- **Mock API layer, every project.** Copies `skills/web-build/templates/js/api/*` to
  `site/js/api/`, replacing `{{project_name}}`, `{{version}}`, and `{{date}}`, and stores
  the SHA-256 of each filled template in `state.yaml`. Creates `site/data/mock/`. For every
  page that holds a section marked `data: true` in the site type, adds
  `<p class="pd-mock-label" data-pd-mock-label hidden>Data contoh</p>` (English page:
  "Sample data") right after the page title, and writes into `js/main.js` the import of
  `watchMockData` and its call. The templates already pass the house ESLint config.
- Dashboards additionally get `js/charts.js`, `js/table.js`, `js/filters.js` (headers
  only) and `js/vendor/chart.umd.js` copied from `node_modules/chart.js/dist/` (Chart.js
  4.5.1 was verified to ship this file). Vendor files are excluded from formatting,
  linting, and the audit.
- Idempotent: refuses to overwrite a non-empty `site/` unless `--force`.

**Accept:** after scaffolding kopi-senja, `npx prettier --check`, `npx stylelint`, and
`npx html-validate` all pass on the untouched skeleton.

### 3.7 `context.py <slug> <page>` (v0.1)

Prints only what building one page needs, as compact lines (linearized triples), so the
agent never loads all project files at once:

```
page | index.html | sections: hero, services, proof
d-typo-1 | typography | grotesk-mono: Archivo Black / Archivo / JetBrains Mono | why: Mono prices …
section | hero | pattern split-offset | layout: Text column and image column of unequal width …
tokens | --pd-color-ink --pd-color-paper … --pd-space-section
component | button | Solid accent fill, ink text in accent-ink, …
signature | Prices and tags set in the mono font like a printed receipt.
placeholders | [[ISI: alamat]] [[ISI: nomor WhatsApp]] …
content | content/id.yaml#index
```

End with the approximate size (`characters / 4` tokens). Target: under 1,500 tokens per page.

### 3.8 `check.py <slug>` (v0.1 core, v0.2 full)

One run = one round. Order of work:

1. **Format** (auto-fix): Prettier `--write` on HTML and CSS, ESLint `--fix` on JS,
   stylelint `--fix` on CSS. Prettier and html-validate use the project's copied configs;
   ESLint and stylelint use the originals in `config/`, because their plugins resolve from
   the config file's location and a project outside the repo cannot reach the repo's
   `node_modules` (see §5). Every tool runs as `node <repo>/node_modules/<pkg>/<bin>`, not
   through `npx`, so the pinned versions are used from any folder.
2. **Lint** (report): html-validate, ESLint, stylelint with JSON formatters → findings with
   `category: lint`. A tool that cannot run, exits with an unexpected code, or prints
   output that is not JSON becomes an `error` finding `tool-failed`, never a silent pass.
3. **Config integrity**: config hashes equal `state.yaml`; mismatch = error
   `config-modified` (restore the original and report).
4. **Conventions** (`category: lint`, own checks): file header in the first 10 lines of every
   file; a banner comment before every `<section>`; a comment above every top-level BEM
   block in CSS; JSDoc with `I.S.` and `F.S.` above every JS function; HTML attribute order;
   commented-out code (a comment whose body parses as a CSS declaration or contains
   `;` plus `(` or `=` in JS).
5. **Audit** (`category: design`): every rule in `audit/anti-slop.yaml`. Rules with
   `pattern` are regexes over the source (visible text only for copy rules; use
   BeautifulSoup to extract text). Rules with `check` are implemented as named functions in
   `lib/audit_rules.py`, one per rule id. Unknown rule ids → fail loudly.
6. **Decision constraints** (`category: design`): evaluate every constraint in
   `decisions.yaml` (`token-equals` on tokens.json; `contrast-min` on token values;
   `var-used` = the last declaration of that property in a rule whose selector list contains
   exactly that selector uses that variable; `pattern-present` = an element with that
   `data-pd-pattern` on that page; `motion-max` = none: no `transition`/`animation`,
   low: only in `:hover`/`:focus-visible`/`[aria-expanded]` rules, medium: unlimited;
   `register` = for `kamu`, no standalone word "Anda" in visible text, and vice versa).
   Report `tfs_auto = passed / total`.
7. **Data layer** (every project with data sections): parse `js/api/endpoints.js` (a plain
   object literal; read it with a small regex parser, no JS runtime needed); every mock file
   validates against `schemas/mock.schema.json`; endpoints and mock files map one to one;
   `client.js` and `mock-label.js` match their stored hashes and `config.js` differs only in
   the three allowed values; the data rules in `audit/anti-slop.yaml` run here. Numbers
   inside `site/data/mock/` are exempt from `unsourced-number`.
8. **Bilingual parity** (when two languages): every number and placeholder in one
   `content/<lang>.yaml` appears in the other.
9. **Signature score**: share of the house-convention checks (prefix, header, banners, BEM
   comments, attribute order, property-group order, decision-id comments present for every
   `realized_by` token used) that pass.

`report.json`:

```json
{
  "round": 2,
  "summary": { "errors": 1, "warnings": 3, "info": 9, "tfs_auto": 0.92, "signature": 0.97 },
  "findings": [
    { "rule": "raw-color", "category": "design", "level": "error",
      "file": "site/css/components.css", "line": 41,
      "message": "#FFFFFF outside tokens.css",
      "fix": "Use the matching var(--pd-color-*) from tokens.css." }
  ]
}
```

**Rounds and stopping.** Copy `site/` to `rounds/<n>/` before writing the report.
Limits: findings with `category: lint` may continue up to round 5; once only `design`
findings remain, at most 2 further rounds. Stop when there are no errors and no warnings,
or a limit is reached. On stop, restore the round with the fewest errors (ties: fewest
warnings, then latest) into `site/`, and print `NEXT: run handoff.py`. Otherwise print
`NEXT: fix the findings in report.json, then run check.py again`.

The two limits differ on purpose: linter feedback is concrete and keeps improving code over
many iterations, while design fixes without precise feedback can make results worse.

**Accept:** a fixture page with a hex color in `components.css`, `href="#"`, a missing
banner, and an `if` without braces produces exactly those findings; after fixing, the next
round reports zero errors; the restore picks the best round.

### 3.9 `handoff.py <slug>` (v0.1)

- Writes `HANDOFF.md` in the brief's first language and prints it: the chosen direction
  and why; assumptions (inferred requirements and sampled decisions); every placeholder
  with its page; every mock endpoint (data the client or a backend must replace); check
  summary (errors, warnings, `tfs_auto`, signature score, semantic review done or skipped);
  where the files are; how to preview: `python -m http.server` inside `site/`, because
  ES modules and `fetch()` do not work when a page is opened as `file://`.
- Writes `API_CONTRACT.md` from `endpoints.js` and the mock files: one section per
  endpoint with method, path, parameters seen in calls to `request()`, and the mock
  response (arrays shortened to their first two items) as the expected shape.
- Writes `provenance.json`: SHA-256 of every file in `site/`, SHA-256 of `decisions.yaml`,
  tool version, ISO timestamp. `--no-provenance` skips this file and removes the
  generator meta tag (for clients who do not want it).

### 3.10 `tools/sync_adapters.py` (v0.1)

- For each `skills/<name>/`, checks that `SKILL.md` frontmatter `name` equals `<name>` and
  the description is under 1,024 characters.
- Creates relative symlinks `.claude/skills/<name>` (Claude Code) and
  `.agents/skills/<name>` (Codex) pointing to `skills/<name>`. `--copy` copies instead
  (Windows without symlink rights). Warns when a `CLAUDE.md` exists.

### 3.11 v0.3: `tools/render_check.py`, `tools/build_cliches.py`, `tools/eval/`

- `render_check.py <slug>`: Playwright screenshots at 1440 and 390 px; axe-core injected
  and run per page (findings into `report.json`, `category: lint`); homogeneity against
  every other project in `projects/`: color distance (CIELCh histogram, Earth Mover's
  Distance) and layout distance (tree edit distance over the landmark and section tree of
  the DOM). Warn when both distances to any earlier project fall below thresholds
  calibrated on the eval set. Note in the report that Design Theater computed layout
  distance from screenshots with OmniParser; ours uses the DOM, so values are not directly
  comparable.
- `build_cliches.py`: given generated copy from the eval harness, count 2- to 5-grams;
  keep n-grams that occur in at least 20% of outputs from at least two different models;
  write `audit/cliches-<lang>.txt`, replacing the seed lists.
- `tools/eval/`: runs conditions C0 (prompt only), C1 (prompt + Anthropic frontend-design
  skill), C2 (this system) over 8 briefs × 3 models × 3 repetitions; collects check
  findings, DHI between briefs, token counts from agent logs; writes one CSV.

### 3.12 v0.4: `tools/export_rdf.py`, `tools/shapes.ttl`

- Exports `brief.yaml` requirements, `decisions.yaml`, and `tokens.json` to RDF (Turtle):
  classes Requirement, Decision, Rationale, Token, Constraint; properties basedOn,
  justifiedBy, realizedBy, verifiedBy.
- Writes each constraint as a SHACL shape; validates with pySHACL against facts extracted
  from the built site; compares the result with `check.py`'s `tfs_auto`.
- Condition C3 of the evaluation: same information as C2, delivered through the ontology.

## 4. Milestones and gates

| Version | Build | Gate (all must pass) |
| --- | --- | --- |
| v0.1 | 3.1, 3.2, 3.4, 3.5, 3.6, 3.7, 3.8 core (steps 1-4, 6, 7), 3.9, 3.10; site types company-profile and dashboard | Two company-profile briefs and one dashboard brief built end to end in Claude Code and in Codex with zero errors from `check.py`; all pytest tests green |
| v0.2 | 3.3, 3.8 full (steps 5, 8, 9), the other three site types, bilingual sites | Between-brief DHI for C2 lower than C0 on a small test (3 briefs × 2 models) |
| v0.3 | 3.11 | Eval harness runs unattended for C0-C2 and writes the CSV |
| v0.4 | 3.12 | C3 runs; automatic TFS agrees with two human raters (Cohen's kappa reported) |

## 5. Tool behaviour: verified and still open

**Verified on 2026-10-08** with Prettier 3.9.9, ESLint 10.12.0 (+ @stylistic, jsdoc),
stylelint 17.16.0 (+ stylelint-order), and html-validate, using the configs in `config/`:

- Prettier keeps single blank lines between CSS declarations, so property-group spacing
  survives formatting.
- `singleAttributePerLine: true` splits every element with two or more attributes, which
  makes HTML needlessly tall. The config therefore sets it to `false`: attributes stay on
  one line while the tag fits in 100 characters and go one per line when it does not.
  `conventions.md` states the rule this way.
- ESLint `--fix` converts braces to Allman and adds blank lines around blocks and braces to
  bare `if`s. It left a trailing space before the moved `{`, so `no-trailing-spaces` was
  added. End-of-line comments are reported, not auto-fixed.
- `jsdoc/require-jsdoc` catches undocumented arrow functions.
- stylelint reports and auto-fixes property order and the blank line between groups; it
  rejects ID selectors, hex colors, non-BEM class names, raw font families, and `!important`.
- html-validate's `doctype-style` conflicts with Prettier's lowercase `<!doctype html>`; the
  rule is turned off. The scaffold skeleton passes Prettier and html-validate.

Pin these versions in `package.json` once v0.1 passes, so behaviour does not drift.

**Verified on 2026-10-08 while making projects work outside the repo:**

- stylelint 17 writes its `-f json` report to **stderr**, not stdout, and has no `--stdout`
  option. `check.py` reads the report with `-o <file>`.
- Normal exit codes: Prettier `--write` 0 (2 = a file failed to parse or the tool failed);
  ESLint 0/1 (2 = crash or bad config); stylelint 0/2 (78 = bad config, 64 = bad option);
  html-validate 0/1.
- From a project folder outside the repo, the copied `eslint.config.js` fails with
  `ERR_MODULE_NOT_FOUND` for `@stylistic/eslint-plugin`, and the copied `.stylelintrc.json`
  fails with "Could not find stylelint-order". With `--config` pointing at `config/` in the
  repo, both work, and ESLint still lints the files under the current directory.
- `npx` run outside the repo falls back to its own cache or downloads the latest versions,
  so the pinned versions are not guaranteed.
- A `site/` that the user turns into a git repo (for deployment) holds read-only object
  files on Windows; `check.py` and `handoff.py` skip `site/.git/`.

**Still to verify:**

1. **Claude Code AGENTS.md support** (2.1.277+, used only when no CLAUDE.md exists) and the
   **Codex skill path** `.agents/skills/`: both taken from third-party articles.
2. **Google Fonts availability** of every family in the style files.

## 6. Tests to write first (v0.1)

- `test_validate_brief.py`, `test_gaps.py`, `test_pick_direction.py` (fixture equality,
  determinism, frequency), `test_compile_tokens.py` (values, contrast rejection),
  `test_scaffold.py` (lint-clean skeleton), `test_check.py` (seeded violations, rounds,
  restore), `test_handoff.py` (placeholders listed, provenance hashes match files).
- A dashboard smoke test: a brief with `site_type: dashboard`, no data source, and three
  metrics must end with one endpoint and one valid mock file per collection, no `fetch()`
  outside `client.js`, the mock label on every data page, chart colors read from tokens,
  an `API_CONTRACT.md`, and zero errors.
- A mock-layer unit test: serve a scaffolded site with `http.server`, load it in
  Playwright (v0.3) or call `client.js` through Node with a stubbed `fetch`, and confirm
  that a mock file without `"_mock": true` throws and that the label becomes visible.
- One end-to-end smoke test that copies the kopi-senja fixtures, runs the scripts in order
  with `--pick dir-2`, writes a minimal hand-made `content/id.yaml` and filled sections, and
  expects `check.py` to report zero errors.
