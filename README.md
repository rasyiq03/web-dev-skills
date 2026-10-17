# ScaffolDev

A Claude Code plugin that turns a short prompt into a finished website: company profile,
landing page, portfolio, small-business catalog, or dashboard, in Indonesian, English, or
both. Every design decision is recorded and every page is formatted, linted, and audited
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

Installed it before the rename to ScaffolDev (as `web-skills@web-dev-skills`)? Remove the
old one first with `/plugin uninstall web-skills@web-dev-skills` and
`/plugin marketplace remove web-dev-skills`, then run the two commands above. The old
dependency cache folder (`web-skills`) can be deleted.

## Use

Open Claude Code in the folder where the site should go and describe it, for example:

```
buat company profile Kopi Senja, kedai kopi di Bandung, target mahasiswa
```

The site is built in `<folder>/<slug>/`, for example `kopi-senja/`:

- `site/`: the website. Preview it with `python -m http.server` inside `site/`, then open
  http://localhost:8000 (pages use ES modules, which do not load from `file://`).
- `HANDOFF.md`: the chosen design direction, assumptions, and every placeholder
  `[[ISI: …]]` still to fill.
- `EXPLAIN.html`: a page for you, the developer: who decided what and why, the design
  decisions with the options that lost, a clickable graph from requirement to code to
  check, and two questions to test your understanding. Double-click to open; no internet
  needed.
- `brief.yaml`, `decisions.yaml`, `content/`: the recorded decisions, kept for later
  changes.

Add "pakai mode interaktif" to the prompt to answer a short questionnaire in the browser
first.

Add "pakai mode terpandu" (or "ajari aku") to learn while it builds: at three checkpoints you
frame the problem, choose the direction, and explain the result back. The help fades as
you pass the checkpoints over several projects (Demonstrasi → Terbimbing → Petunjuk →
Mandiri); your level is kept in `profile.yaml` next to the dependency cache.

Changed your mind about one decision? Ask for it ("ganti paletnya jadi sun-block, karena
pelanggan suka warna cerah"). Only what depends on that decision is redone, and the reason
is recorded. Ask "kenapa pakai font ini?" to get the chain of reasons.

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
Sites built while Claude Code is open in the clone go to `projects/<slug>/`.
`python -m pytest --network` also runs the slow tests that install dependencies from the
internet. For Codex, `python tools/sync_adapters.py` links the skills into `.agents/skills/`.

`IMPLEMENTATION.md` specifies every script.

## License

MIT
