# Dogfood: portfolio, dashboard, interactive mode, and other agents, 2026-11-02

The last site types and modes that had only tests, plus a check that the skills run
outside Claude Code.

| Build | Site type | Mode | Result |
| --- | --- | --- | --- |
| Rina Pratiwi, illustrator in Makassar (`examples/rina-ilustrasi/`) | portfolio, 4 pages | interactive (question form) | check 0 errors, 0 warnings |
| Toko Kue Bunda, Medan (`examples/kue-bunda-dashboard/`) | dashboard, 2 pages, mock API | auto | check 0 errors, 0 warnings; KPIs, charts, filter, and table sorting work in a browser |
| Kopi Senja from the plugin copy Codex installs | company profile | auto, scripts only | 0 errors, 0 warnings with `python -S` and no `CLAUDE_PLUGIN_ROOT` |

The client in the question form, and the agent of the Codex run, were simulated: the form
was filled through a browser at 360 px, and the Codex run fed the scripts the same steps a
Codex agent would. A build driven by a Codex model needs an OpenAI login; Antigravity's
installer was not allowed in this session, so its paths follow Google's codelab.

## Found and fixed

| Found | Effect | Fix |
| --- | --- | --- |
| A question the client left empty was asked again | interactive mode looped: `gaps` sent the agent back to `serve` forever | `serve` records the questions shown in `state.yaml`; `gaps` asks only new ones and moves on |
| The form said "Kuesioner Brief — rina-ilustrasi" | jargon and a slug for a client; mixed "Anda"/"kamu"; one-line boxes for long answers | title with the business name, no pronouns, textareas, messages in the page language |
| `check` did not test internal links | three nav links from `pages/` pointed to missing files and still passed | `broken-link` error for local `href`/`src` that do not resolve |
| Display headings overflowed at 360 px | a long word in a large serif scrolled the page sideways | `base.css` headings get `hyphens: auto` and `overflow-wrap: break-word` |
| Filter options counted as facts and data | "7 hari terakhir" failed `unsourced-number` and `hardcoded-data` | numbers inside `<select>` are skipped |
| Chart.js axes in `en-US`, rupiah with a space | "3,500,000" and "Rp 11.595.000" on an Indonesian dashboard | `dashboard.md`: `options.locale` and `Rp25.000`; fixed in the build |
| Dashboard navigation only on `index` | the data page was a dead end | `dashboard.md`: repeat the tabs in every other page's header |
| Work patterns promised thumbnails | `case-list` and `index-table` assumed photos the brief did not have | images only when photos are stated |
| `${CLAUDE_PLUGIN_ROOT}` explained late and for Claude only | other agents met the variable before the rule | one rule near the top of each SKILL.md, for any agent |
| No way to install the skills globally for Antigravity | only `.agents/skills/` inside the repository | `sync_adapters.py --target ~/.gemini/config/skills` (links, never copies, outside the repo) |

## Still not tried

- A build driven by a Codex model, and anything inside Antigravity.
- Guided mode with a real developer.
