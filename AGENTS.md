# Website builder

This repository turns a short prompt into a finished website, with every design
decision recorded and every page checked before handoff.

- To build or redesign a site, follow `skills/web-build/SKILL.md`.
- Projects live in `projects/<slug>/`, or in `$PD_PROJECTS_DIR/<slug>/` when that
  environment variable is set. Each run writes only inside its own project folder.
- Scripts run from the repository root with `python skills/web-build/scripts/<name>.py <slug>`.
- Files in `config/` and `audit/` are fixed; change them only when the user asks.

Setup (once): `pip install -r requirements.txt` and `npm run setup`.
