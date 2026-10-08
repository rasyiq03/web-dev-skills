# web-skills

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
/plugin install web-skills@web-dev-skills
```

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
- `brief.yaml`, `decisions.yaml`, `content/`: the recorded decisions, kept for later
  changes.

Add "pakai mode interaktif" to the prompt to answer a short questionnaire in the browser
first.

## First run and the dependency cache

The first build on a machine installs the Python packages and Node tools the checks need
(about a minute, needs internet). They go to a cache that later builds reuse:

- Windows: `%LOCALAPPDATA%\web-skills`
- macOS and Linux: `~/.cache/web-skills`

Set `PD_CACHE_DIR` to use another folder. Uninstalling the plugin does not remove the
cache; delete the folder by hand.

## Update

```
/plugin marketplace update web-dev-skills
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
`/plugin marketplace add <path to the clone>` and `/plugin install web-skills@web-dev-skills`.
Sites built while Claude Code is open in the clone go to `projects/<slug>/`.
`python -m pytest --network` also runs the slow tests that install dependencies from the
internet. For Codex, `python tools/sync_adapters.py` links the skills into `.agents/skills/`.

`IMPLEMENTATION.md` specifies every script.

## License

MIT
