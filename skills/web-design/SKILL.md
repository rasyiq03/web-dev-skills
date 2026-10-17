---
name: web-design
description: Choose the visual direction for a website project - style, palette, typography, layout patterns, motion, and tone. Use during step 3 of web-build, or when the user asks to restyle an existing project.
---

# web-design

Propose five genuinely different design directions for one brief and say how typical each
one is. A script then picks one, so different clients get different sites while each site
stays internally consistent. Your only output is `<project>/directions.yaml`.

## Read first

`<project>` is the folder printed by web-build step 1. If `${CLAUDE_PLUGIN_ROOT}` appears
literally in this file, it means the folder that contains `skills/`.

1. `<project>/brief.yaml` and `<project>/gaps.json` (it lists the requirement ids, such as
   `req-audience`, that your rationale cites).
2. `${CLAUDE_PLUGIN_ROOT}/skills/web-design/styles/index.yaml`: one line per style. Read
   only this catalog first, then open the full file of each style you actually use.
3. `${CLAUDE_PLUGIN_ROOT}/skills/web-design/layouts/patterns.yaml`: the layout patterns for
   each section kind.
4. For a business in Indonesia or a brief with `id`:
   `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/indonesia.md` (phone-first, WhatsApp,
   trust signals, and local identity from the brief rather than ornament).

## Rules

- Exactly 5 directions. Each `probability` (0 to 1) estimates how often a typical designer
  would produce that direction for this brief; the five sum to 1.
- Directions differ on at least three axes: style, palette, type pairing, layout, motion,
  tone.
- A style or brand palette named in the brief stays in every direction; vary the rest.
- Every rationale line names something specific to this brief (audience, place, product,
  or goal). A line that would fit any business needs rewriting.
- `based_on` lists requirement ids exactly as `gaps.json` prints them.
- The file must pass `${CLAUDE_PLUGIN_ROOT}/skills/web-build/schemas/directions.schema.json`;
  `pick_direction` reports any mismatch.

## Shape of one direction

```yaml
directions:
  - id: dir-1
    probability: 0.30
    style: neobrutalism          # id from styles/index.yaml
    palette: warm-paper          # palette id from that style file, or custom
    type_pairing: grotesk-mono   # pairing id from that style file, or custom
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

## Custom values

When no library palette or pairing fits (for example, the client's brand colors):

- `palette: custom` plus a `colors` map with `ink`, `paper`, `accent`, `muted`, and
  `accent-ink` as hex values. The compile step rejects pairs below WCAG AA contrast.
- `type_pairing: custom` plus a `fonts` map with `display`, `body`, and `mono` family names
  from Google Fonts.
