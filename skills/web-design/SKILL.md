---
name: web-design
description: Choose the visual direction for a website project - style, palette, typography, layout patterns, motion, and tone. Use during step 3 of web-build, or when the user asks to restyle an existing project.
---

# web-design

Your job is to propose several genuinely different design directions for one brief and
state how typical each one is. A script then picks one, so different clients end up with
different sites while each site stays internally consistent.

## Inputs

- `<project>/brief.yaml` and `<project>/gaps.json` (it lists requirement ids such as
  `req-audience` that your rationale must cite). `<project>` is the folder printed by
  `python "${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py" path <slug>`; web-build
  step 1 has already run it.
- `${CLAUDE_PLUGIN_ROOT}/skills/web-design/styles/index.yaml`: one line per style. Read only
  this catalog first, then open the full file of each style you actually use.
- `${CLAUDE_PLUGIN_ROOT}/skills/web-design/layouts/patterns.yaml`: the layout patterns
  available for each section kind.

If `${CLAUDE_PLUGIN_ROOT}/skills` appears literally in this file (the skill was loaded
without plugin support), it means the folder that contains this skill's folder.

If the brief names a style (for example "neobrutalism") or a brand palette, every
direction keeps it and varies only the other axes.

## Write `<project>/directions.yaml`

Propose exactly 5 directions. Give each a `probability` between 0 and 1 that estimates how
often a typical designer would produce this direction for this brief; the five values sum
to 1. Make the directions differ on at least three of these axes: style, palette,
type pairing, layout patterns, motion, tone.

```yaml
directions:
  - id: dir-1
    probability: 0.30
    style: neobrutalism          # id from styles/index.yaml
    palette: warm-paper          # palette id from that style file
    type_pairing: grotesk-mono   # pairing id from that style file
    layout:                      # section id (from site-types) -> pattern id (layouts/patterns.yaml)
      hero: split-offset
      services: list-with-prices
      contact: map-band
    motion: low                  # none | low | medium
    tone: warm-casual            # guides the copy in web-build step 5
    register: { id: kamu }       # pronoun per language: id -> kamu | Anda, en -> you
    summary: Thick borders and paper tones, like a hand-stamped cafe menu.
    rationale:
      style: A hand-stamped look feels made by the owner, not by a franchise.
      color: Warm paper tones set it apart from the chain cafes nearby.
      typography: Monospace accents echo the price lists students already read.
      layout: The offset hero leaves room for the menu photo the client will supply.
      motion: Hover feedback only, so the menu loads fast on phone data.
      tone: Students expect a casual register and the pronoun "kamu".
    based_on: [req-audience, req-business.location]
```

Each rationale line names something specific to this brief: the audience, the place, the
product, or the business goal. A rationale that would fit any business needs rewriting.
`based_on` lists requirement ids exactly as `gaps.json` prints them. The file must pass
`${CLAUDE_PLUGIN_ROOT}/skills/web-build/schemas/directions.schema.json`; `pick_direction`
reports any mismatch.

## Custom values

When no palette or pairing in the library fits the brief (for example, the client's brand
colors), set `palette: custom` and add a `colors` map with `ink`, `paper`, `accent`, `muted`,
and `accent-ink` as hex values. Likewise set `type_pairing: custom` and add a `fonts` map with
`display`, `body`, and `mono` family names from Google Fonts. The compile step checks
contrast and rejects pairs below WCAG AA.
