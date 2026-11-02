# Dogfood: deep mode and guided mode, 2026-10-30

Two builds run end to end with the plugin's scripts, to test the two modes that had only
unit tests so far.

| Build | Mode | Site type | Languages | Result |
| --- | --- | --- | --- | --- |
| Keripik Bu Sari, Kediri (`examples/keripik-bu-sari/`) | deep | umkm-catalog, 3 pages | id | 4 sittings by mufakat, check 0 errors and 0 warnings, "Siap pakai" |
| Sekar Jagad batik workshop, Yogyakarta (`examples/batik-sekar-jagad/`) | guided, level 2 | landing, 1 page × 2 languages | id, en | 3 checkpoints passed, check 0 errors and 0 warnings |

## Deep mode: what the council did

All four sittings ran with real subagents (5 in round 1, 5 in round 2, and only the
blocking members in round 3), so none is marked `simulated`. The minutes are in
`examples/keripik-bu-sari/deliberation/`.

- **direction:** round 1 split 3–2 (dir-1 against dir-3). The Arsitek and the Penguji had
  argued from two wrong claims (that kunyit fails contrast; that dir-3 uses one font
  family). Once the chair shared the measured ratios and the font list, both corrected
  themselves and moved to dir-1. Evidence, not seniority, decided.
- **copy:** the Wakil klien vetoed three invented facts in the Penulis's draft ("goreng",
  "andalan", and Bu Sari herself cooking and answering chats). The revision round removed
  them; payment methods became a new placeholder instead of QRIS/COD guesses.
- **first-page:** the Perancang proposed "Dari dapur Bu Sari" and four members blocked it
  because it revived the copy veto. The Perancang also blocked on a real gap: the palette
  called kunyit had no turmeric yellow at all.
- **site:** the Penguji blocked on WCAG 2.5.3 (per-product buttons must not use an
  `aria-label` that differs from the visible text) and on stale line numbers in the check
  report, which turned out to be a bug in `check.py`.

Cost: about 30 subagent calls for the whole site, within the budget in `mode-deep.md`.

## Guided mode

The developer was simulated: the answers at each checkpoint were written by the agent and
marked so in the notes. What this run tests is the mechanics, not the teaching.

- Framing, direction, and acceptance were recorded; the direction checkpoint took the
  feedback path (a vague first reason, one hint, then a reason that names the audience and
  the product).
- `pick_direction --pick` plus `decide --accept` made the developer the owner of all six
  decisions (P1 6/6, P6 low).
- The profile records the project once even when handoff runs twice, and the level stays
  at 2 after one fully passed project (it drops after two in a row).

## Found and fixed

| Found | Effect | Fix |
| --- | --- | --- |
| State colors searched from the dark end | `--pd-color-positive` was `#001100`, near black, in every project | search from the paper's lightness outward; test that hue survives |
| Palettes had no signature surface | "kunyit" showed only brown and cream | optional `tint` per palette, compiled to `--pd-color-tint`, contrast-checked |
| `context` omitted radius tokens | the agent could not round corners with tokens | radius in the token list |
| Placeholders written on pages were not in the graph | `[[ISI: cara pembayaran]]` could not be cited as evidence | `ph:site:<text>` nodes from the pages |
| Council packets said "run context yourself" | members had to explore instead of judge | packets list sections, file paths, CSS, and token ids, and ask for quoted YAML |
| `endpoints.js` comment example counted as an endpoint | a false `mock-file-invalid` error | comments stripped before parsing |
| Sample label required on every data page | a catalog written from the brief failed | label required only when endpoints exist |
| An unbuilt page passed check | "run handoff" while two pages were empty shells | `section-empty` warning |
| `banner-missing` looked 4 lines back | missed a section placed right after another | the banner must be the line right above |
| Round snapshot taken before formatting | restored files did not match report line numbers | snapshot after formatting; test |
| Handoff said "1 finding" for a fixed a11y issue | read as an open problem | `applied` per finding, counted in the handoff |
| `context` ignored the second language | `en/index.html` and `content/en.yaml` unmentioned | a `translation` line per extra language |
| A comma inside `[a, b]` split a sentence | half a paragraph vanished from the page | SKILL step 5 rule, and `bilingual-structure-mismatch` warning |
| Tests replaced one-line section tags | the skeleton is formatted over several lines, so the e2e test filled nothing | regex helper `fill_empty_sections` |

## Kept as is

- `run path` prints the folders without creating them, on purpose (tested); the agent's
  Write tool creates the folder.
- Fonts come from Google Fonts through `fonts.html`; the Arsitek's proposal to self-host
  them was withdrawn in the minutes.
