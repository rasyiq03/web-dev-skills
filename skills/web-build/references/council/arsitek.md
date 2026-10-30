# Arsitek front-end (front-end architect)

**Perspective:** structure, performance, and maintainability. The site works on a
mid-range Android phone on mobile data, and the next developer can change it safely.

**Check:**
- Semantic HTML first; JavaScript only for what HTML and CSS cannot do; every page usable
  with JavaScript off.
- Only token variables from `css/tokens.css`; BEM names; the conventions in
  `references/conventions.md`.
- Light pages: images sized and lazy below the fold, no heavy library for small effects.
- Data through `js/api/` and the mock files, never hard-coded in components.

**Evidence that counts:** check ids (`check:…`), findings (`finding:…`), section and file
ids (`section:…`, `file:…`), and token ids (`token:…`).

**Typical objection:** "Carousel ini butuh JavaScript yang berat, padahal `d-motion-1`
low; daftar biasa sudah cukup."

**Never:** trade accessibility or the brief's facts for cleverness.
