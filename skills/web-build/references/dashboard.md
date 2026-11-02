# Dashboard conventions

Read this together with `conventions.md` when the site type is `dashboard`. All data still
goes through `js/api/` as described there.

- The `shell` section (navigation) is a section of `index` only; put the same tabs in the
  header of every other page, such as `pages/data.html`, so no page is a dead end.
- Files: `js/charts.js` draws charts, `js/table.js` renders and sorts tables,
  `js/filters.js` applies filters; `main.js` wires them together. One function per widget,
  each fetching through `request()`.
- Format numbers and dates with `Intl.NumberFormat` and `Intl.DateTimeFormat` in the page
  language (`id-ID` or `en-US`). For rupiah, remove the space `Intl` puts after `Rp`
  (`Rp25.000`, as `indonesia.md` writes it). Give every chart `options.locale` in the same
  language; Chart.js otherwise labels its axes in `en-US` ("3,500,000").
- Charts use Chart.js from `js/vendor/chart.umd.js` (copied there by the scaffold). Read
  colors at runtime from the tokens, for example
  `getComputedStyle(document.documentElement).getPropertyValue('--pd-color-chart-1')`;
  series colors follow `--pd-color-chart-1` … `-6`, and states use `--pd-color-positive`,
  `--pd-color-negative`, `--pd-color-warning`.
- Every chart has a title, the unit, and the period in text, plus a text alternative: an
  `aria-label` summary on the canvas and the same data in a visually hidden `<table>`.
- Tables are real `<table>` elements with `<caption>`, `<th scope="col">`, and numbers
  right-aligned through a class.
- A KPI shows label, value, unit, period, and change as separate elements, so each can be
  styled and read on its own.
