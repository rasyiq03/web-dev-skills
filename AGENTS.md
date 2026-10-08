# Website builder

This repository turns a short prompt into a finished website, with every design
decision recorded and every page checked before handoff. It is also the Claude Code
plugin `web-skills`; `README.md` explains installing it.

- To build or redesign a site, follow `skills/web-build/SKILL.md`.
- Projects live in `projects/<slug>/` while you work in this repository, in
  `<folder>/<slug>/` when the plugin runs elsewhere, and in `$PD_PROJECTS_DIR/<slug>/`
  when that variable is set. `python skills/web-build/scripts/run.py path <slug>` prints
  the folder. Each run writes only inside its own project folder.
- Scripts run from the repository root with
  `python skills/web-build/scripts/run.py <name> <slug>`.
- Files in `config/` and `audit/` are fixed; change them only when the user asks.

Development setup (once): `pip install -r requirements.txt -r requirements-dev.txt`,
`npm run setup`, then load this folder as the plugin (see "Development" in `README.md`).
