# ScaffolDev

A Claude Code plugin that turns a short prompt into a finished website: company profile,
landing page, portfolio, small-business catalog, or dashboard, in Indonesian, English, or
both. It ships five visual styles (Neobrutalism, Editorial, Clean Swiss, Soft
Organic, Data Utility), each with three contrast-checked palettes and three font pairings. Every design decision is recorded and every page is formatted, linted, and audited
before handoff.

## Requirements

- [Claude Code](https://claude.com/claude-code)
- Python 3.11 or newer, reachable as `python`. On Windows, install it from python.org; the
  Microsoft Store shortcut named `python` is not a real install.
- Node.js LTS (includes `npm`).

## Install

In Claude Code:

```
/plugin marketplace add rasyiq03/web-dev-skills
/plugin install scaffoldev@scaffoldev
```

The skills appear as `scaffoldev:web-build` and `scaffoldev:web-design`.

Or add it from the app: use `rasyiq03/web-dev-skills` (or
`https://github.com/rasyiq03/web-dev-skills.git`) as the marketplace source, then install
**scaffoldev**. To try an unmerged branch, append it to the git URL:
`https://github.com/rasyiq03/web-dev-skills.git#<branch>`.

Update with `/plugin marketplace update scaffoldev`. Claude Code and Codex install a new
copy only when the version changes, so raise it with every release in
`.claude-plugin/`, `.codex-plugin/`, and `.antigravity-plugin/plugin.json` (a test keeps them equal).

In Codex (0.166 or newer):

```
codex plugin marketplace add rasyiq03/web-dev-skills
codex plugin add scaffoldev@scaffoldev
```

For an unmerged branch, use `rasyiq03/web-dev-skills@<branch>` as the source. Codex lists
the skills as `scaffoldev:web-build` and `scaffoldev:web-design`. Older Codex versions can
use `python tools/sync_adapters.py`, which links the skills into `.agents/skills/`.

In Google Antigravity (CLI `agy` 1.4 or newer), install it from a clone of this repository:

```
git clone https://github.com/rasyiq03/web-dev-skills.git
agy plugin install web-dev-skills
```

Already have it in Claude Code? `agy plugin import claude` copies it over. Antigravity lists
the skills as `web-build` and `web-design`. To update, run `git pull` in the clone and
install again. Without the plugin system, `python tools/sync_adapters.py --target
~/.gemini/config/skills` links the skills instead; links, not copies, because the scripts
need the clone's `audit/` and `config/` folders.

The first run installs Python packages and Node tools into a cache folder. When an update
needs new versions, the new cache replaces the old one automatically.

Installed it before the rename to ScaffolDev (as `web-skills@web-dev-skills`)? Remove the
old one first with `/plugin uninstall web-skills@web-dev-skills` and
`/plugin marketplace remove web-dev-skills`, then run the two commands above. Its old
dependency cache (`web-skills`) is deleted on the first run.

## Use

Open Claude Code in the folder where the site should go and describe it, for example:

```
buat company profile Kopi Senja, kedai kopi di Bandung, target mahasiswa
```

The site is built in `<folder>/<slug>/`, for example `kopi-senja/`. That folder holds only
the website (`index.html`, `pages/`, `css/`, `js/`, `data/`, `assets/`). Preview it with
`python -m http.server` inside it, then open http://localhost:8000 (pages use ES modules,
which do not load from `file://`).

Everything else ScaffolDev made is in `kopi-senja/.ScaffolDev/`. Delete that folder when you
no longer need it and the site stays untouched:

- `HANDOFF.md`: the chosen design direction, assumptions, every placeholder `[[ISI: …]]`
  still to fill, and the learning signals.
- `EXPLAIN.html`: a page for you, the developer: who decided what and why, the design
  decisions with the options that lost, a clickable graph from requirement to code to
  check, and two questions to test your understanding. Double-click to open; no internet
  needed.
- `brief.yaml`, `decisions.yaml`, `content/`, `graph.json`, `trace.jsonl`: the recorded
  decisions and their history, kept for later changes.

Projects built with an older version (files next to a `site/` folder) are moved into this
layout automatically the first time ScaffolDev opens them.

Add "pakai mode interaktif" to the prompt to answer a short questionnaire in the browser
first.

Add "pakai mode terpandu" (or "ajari aku") to learn while it builds: at three checkpoints you
frame the problem, choose the direction, and explain the result back. The help fades as
you pass the checkpoints over several projects (Demonstrasi → Terbimbing → Petunjuk →
Mandiri); your level is kept in `profile.yaml` next to the dependency cache.

Add "mode deep work" (or "mode musyawarah", "langsung jadi") for one prompt in and a ready
site out: five AI roles (Perancang, Penulis, Arsitek front-end, Penguji mutu, Wakil klien)
deliberate at four sittings until they agree (*musyawarah untuk mufakat*), the Wakil klien
vetoes any invented fact, and the minutes land in `deliberation/`. It uses several times
more tokens than the default mode.

Changed your mind about one decision? Ask for it ("ganti paletnya jadi sun-block, karena
pelanggan suka warna cerah"). Only what depends on that decision is redone, and the reason
is recorded. Ask "kenapa pakai font ini?" to get the chain of reasons.

With Chrome or Chromium installed, the agent also runs `tools/render_check.py`: every page
is opened at desktop and phone width, checked with axe-core for accessibility, for sideways
scrolling, and for script errors, and compared with your other projects so two clients do
not get the same site. Screenshots land in `.ScaffolDev/render/`.

## First run and the dependency cache

The first build on a machine installs the Python packages and Node tools the checks need
(about a minute, needs internet). They go to a cache that later builds reuse:

- Windows: `%LOCALAPPDATA%\scaffoldev`
- macOS and Linux: `~/.cache/scaffoldev`

Set `PD_CACHE_DIR` to use another folder. Uninstalling the plugin does not remove the
cache; delete the folder by hand.

## Update

```
/plugin marketplace update scaffoldev
```

## Development

```
git clone https://github.com/rasyiq03/web-dev-skills.git
cd web-dev-skills
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
npm run setup
python -m pytest
```

Load the working copy as the plugin, so edits apply without reinstalling: in Claude Code,
`/plugin marketplace add <path to the clone>` and `/plugin install scaffoldev@scaffoldev`.
Sites built while Claude Code is open in the clone go to `projects/<slug>/` (with their
`.ScaffolDev/` inside).
`python -m pytest --network` also runs the slow tests that install dependencies from the
internet. For Codex, `python tools/sync_adapters.py` links the skills into `.agents/skills/`.

`python tools/eval/collect.py <folder> --out eval-results.csv` collects every project in a
folder into one CSV (mode, check scores, the Agentivism signals P1–P6, checkpoints, council
sittings) to compare auto, guided, and deep work.

`IMPLEMENTATION.md` specifies every script.

### Research tools

- `python tools/eval/harness.py --out DIR --models sonnet --dry-run`: plans an evaluation of
  conditions C0 (prompt only), C1 (frontend-design skill), and C2 (ScaffolDev) over the
  briefs in `tools/eval/briefs.yaml`; without `--dry-run` it runs Claude Code for each and
  writes `eval.csv` with tokens, cost, browser findings, and the design homogeneity index.
  A full grid costs real money; start with `--only` and `--reps 1`.
- `python tools/build_cliches.py DIR`: turns the harness runs into a cliché list.
- `python tools/export_rdf.py <slug>`: exports a project's decisions to RDF and checks its
  constraints with SHACL (`pip install -r requirements-dev.txt` first).

## License

MIT
