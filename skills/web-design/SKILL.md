---
name: web-design
description: Choose the visual direction for a website project - style, palette, typography, layout patterns, motion, and tone. Use during step 3 of web-build, or when the user asks to restyle an existing project.
---

# web-design

Propose five genuinely different design directions for one brief and say how typical each
one is. A script then picks one, so different clients get different sites while each site
stays internally consistent. Your only output is `<work>/directions.yaml`.

## Read first

`<work>` is the `WORK:` folder printed by web-build step 1 (`<project>/.ScaffolDev/`).
If `${CLAUDE_PLUGIN_ROOT}` appears literally in this file, it means the folder that contains
`skills/`.

1. `<work>/brief.yaml` and `<work>/gaps.json` (it lists the requirement ids, such as
   `req-audience`, that your rationale cites).
2. `${CLAUDE_PLUGIN_ROOT}/skills/web-design/styles/index.yaml`: one line per style. Read
   only this catalog first, then open the full file of each style you actually use.
3. `${CLAUDE_PLUGIN_ROOT}/skills/web-design/layouts/patterns.yaml`: the layout patterns for
   each section kind.
4. For a business in Indonesia or a brief with `id`:
   `${CLAUDE_PLUGIN_ROOT}/skills/web-build/references/indonesia.md` (phone-first, WhatsApp,
   trust signals, and local identity from the brief rather than ornament).

## How to build the five directions

1. **Anchor on the brief.** Before choosing anything, name three anchors: *who* (the
   audience sets formality and register), *where* (the place or community sets palette
   mood and local detail), and *what* (the offer sets type and layout). Every direction
   serves all three; they differ in how.
2. **Filter styles by formality.** Health, law, finance, government, and education use only
   `formal` or `neutral` styles; youth, food, events, and creative work may use any. Read
   `fits` and `avoid` in the catalog and skip a style whose `avoid` names this business.
3. **Spread the styles.** Use at least three different styles across the five when the
   filter leaves three or more. A style or brand palette named in the brief is the exception:
   keep it in every direction and vary the other axes.
4. **Spread the probabilities.** The script samples by probability, so the spread decides
   how often clients get the obvious site. Give the most fitting conventional direction
   0.30–0.40, two credible variants 0.15–0.25 each, and one bold but defensible direction
   0.05–0.12. Never make all five nearly equal.
5. **Pick layouts the brief can fill.** Prefer patterns whose `needs` (in `patterns.yaml`)
   are stated in the brief. Without stated photos, use a type-led hero (`full-bleed-type`,
   `stacked-statement`); without client names or quotes, use `facts-ledger` for proof. A
   direction that uses a pattern with unmet needs gets at most 0.15.
6. **Match motion and register to the audience.** Motion `none` or `low` for formal sectors,
   phone-first audiences, and dashboards; `medium` only when the brief asks for liveliness.
   Register "Anda" for formal sectors and older audiences, "kamu" for students and youth.

## Rules the script checks

- Exactly 5 directions; the five probabilities sum to 1.
- Any two directions differ on at least three axes: style, palette, type pairing, layout,
  motion, tone.
- Every rationale line names something specific to this brief (audience, place, product,
  or goal). A line that would fit any business needs rewriting.
- `based_on` lists requirement ids exactly as `gaps.json` prints them.
- The file must pass `${CLAUDE_PLUGIN_ROOT}/skills/web-build/schemas/directions.schema.json`;
  `pick_direction` reports any mismatch and warns about patterns whose needs are missing.

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
  from Google Fonts. Add `display_weight: 400` when the display family has no bold (many
  display serifs and poster faces); headings default to 700.
