# Code conventions

Write every file this way. The formatter and linters in `check.py` enforce most of it;
writing it right the first time saves fix rounds.

## Layout of a project

```
site/
	index.html
	pages/            other pages, e.g. tentang.html
	css/
		tokens.css      generated, never edit
		base.css        reset and element defaults
		layout.css      containers, grids, sections
		components.css  BEM components
		pages/          styles used by one page only
	js/
		main.js         entry point
		components/     one file per interactive component
		api/            config.js, client.js, endpoints.js, mock-label.js
		vendor/         third-party files copied by the scaffold, never edited
	data/mock/        <name>.mock.json, one per endpoint in endpoints.js
	assets/img/  assets/fonts/
```

HTML holds content, CSS holds all styling, JavaScript holds only behaviour HTML and CSS
cannot do. Every page stays readable and navigable with JavaScript off. Load CSS in the
order tokens, base, layout, components, pages.

## Whitespace and density

- Indent with one tab. Keep lines within 100 characters.
- One statement, one declaration, one selector per line.
- One blank line between functions, between CSS rules, between HTML sections, and before
  and after every `if`, `for`, `while`, and `switch` block.
- JavaScript functions stay within 30 lines and 4 levels of nesting; split anything longer
  into named helpers.

## Naming

| Thing | Style | Example |
| --- | --- | --- |
| CSS class | BEM, prefix `pd-` | `pd-menu-card`, `pd-menu-card__price`, `pd-menu-card--featured` |
| CSS variable | `--pd-{category}-{role}-{state}` | `--pd-color-accent-hover` |
| Data attribute | `data-pd-{name}` | `data-pd-target` |
| HTML id | kebab-case, anchors and form labels only | `#kontak` |
| JS variable | camelCase noun | `menuItems` |
| JS function | camelCase, starts with a verb | `openMenu()` |
| JS constant | UPPER_SNAKE_CASE | `MAX_SLIDES` |
| File | kebab-case | `menu-card.js` |

Names are in English and describe the role (`pd-menu-card__price`), never the look.
Comments are in Indonesian.

## HTML

- Semantic elements: `header`, `nav`, `main`, `section`, `article`, `footer`; one `h1`
  per page; headings in order; `button` for actions, `a` for navigation.
- Attributes stay on one line while the tag fits in 100 characters; a longer tag gets one
  attribute per line (Prettier does this for you). Order: `class`, `id`, `name`, `type`,
  `href`/`src`, `alt`, `data-pd-*`, `aria-*`.
- Alt text describes what the image shows for this page; decorative images use `alt=""`.

## CSS

Group properties in this order with one blank line between groups:
position, box (`display`, flex/grid, `gap`, size, `margin`, `padding`), typography
(`font-*`, `line-height`, `letter-spacing`, `color`, `text-*`), visual (`background`,
`border`, `border-radius`, `box-shadow`), motion (`transform`, `transition`, `animation`).
Every color, font, size, and spacing value comes from `var(--pd-...)`. Style with classes;
nest at most two levels.

## JavaScript

Allman braces, braces on every `if`, a `default` in every `switch`, `const` by default.
Repeated text becomes a constant or a function.

## Data and the mock API

Data means collections and figures a backend would normally supply: dashboard metrics and
table rows, catalog products, portfolio projects, orders. Content is everything stated in
the brief, including a product list the client gave you: write it straight into the HTML.
Single facts the brief lacks (address, hours) become `[[ISI: ...]]` placeholders.
Collections the brief lacks, and every dashboard figure, go through the mock API below.
Testimonials, reviews, and quotes are never mock data; they stay placeholders until the
client supplies real ones.

- **All data goes through `js/api/`.** The scaffold provides `config.js`, `client.js`, and
  `mock-label.js`; keep them as they are. You add one entry per endpoint in `endpoints.js`:
  `metrics: { method: 'GET', path: '/metrics', mock: 'metrics' }`. Name endpoints and paths
  the way a real REST API for this business would.
- **Components ask the API, never the file.** A component imports
  `request` from `js/api/client.js` and calls `await request('metrics', { from, to })`.
  `fetch()` appears only in `client.js`; HTML and components contain no data literals.
- **Each endpoint has one mock file**: `site/data/mock/<mock>.mock.json`, shaped by
  `schemas/mock.schema.json`:

```json
{
  "_mock": true,
  "endpoint": "GET /metrics",
  "generated_by": "pd-web-skills 0.1",
  "data": [{ "date": "2026-09-01", "revenue": 1250000, "orders": 42 }]
}
```

- **The response shape is the contract.** Put in `data` exactly what the real endpoint
  should return; switching to the real API changes only `API_MODE` and `API_BASE_URL` in
  `config.js`.
- **The sample label is automatic.** Every page that shows data has
  `<p class="pd-mock-label" data-pd-mock-label hidden>Data contoh</p>` near its title (the
  scaffold adds it), and `main.js` calls `watchMockData()`. The label appears whenever a
  mock response arrives.
- Mock values are plausible for this business and its scale, round where real data would
  be round, and use invented names only for records such as orders or customers in a table.

## Dashboards

- Files: `js/charts.js` draws charts, `js/table.js` renders and sorts tables,
  `js/filters.js` applies filters; `main.js` wires them together. One function per widget,
  each fetching through `request()`.
- Format numbers and dates with `Intl.NumberFormat` and `Intl.DateTimeFormat` in the page
  language (`id-ID` or `en-US`).
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

## Comments

Comments say why; the code already says what. Place them on the line above the code.

File header, first thing in every file (HTML: right after `<!doctype html>`, inside `<!-- -->`):

```css
/* ============================================================
 * File      : components.css
 * Proyek    : Kopi Senja
 * Deskripsi : Komponen kartu menu, tombol, dan navigasi
 * Dibuat    : sistem skill website v0.1, 2026-10-08
 * ============================================================ */
```

Section banner before every HTML section, every CSS component group, every JS module part:

```css
/* ============================================================ */
/* ========================= MENU CARD ======================== */
/* ============================================================ */
```

One line above every BEM block naming its job and modifiers:
`/* Kartu satu item menu. Modifier: --featured (menu andalan). */`

The decision id above every rule that realizes a design decision from `decisions.yaml`:
`/* d-typo-1: display serif berkarakter */`

JSDoc above every function, with I.S. and F.S.:

```js
/**
 * Membuka atau menutup menu navigasi pada layar kecil.
 *
 * I.S. : Menu dalam keadaan terbuka atau tertutup.
 * F.S. : Keadaan menu berbalik; aria-expanded mengikuti keadaan baru.
 *
 * @param {HTMLElement} toggle Tombol menu yang diklik pengguna.
 * @returns {void}
 */
function toggleMenu(toggle)
{
	const nav = document.querySelector(toggle.dataset.pdTarget);

	if (!nav)
	{
		return;
	}

	const isOpen = nav.classList.toggle(MENU_OPEN_CLASS);

	toggle.setAttribute('aria-expanded', String(isOpen));
}
```

## Reference CSS rule

```css
/* Kartu satu item menu. Modifier: --featured (menu andalan). */
.pd-menu-card {
	position: relative;

	display: grid;
	gap: var(--pd-space-sm);
	padding: var(--pd-space-md);

	/* d-typo-1: display serif berkarakter */
	font-family: var(--pd-font-display);
	color: var(--pd-color-ink);

	background: var(--pd-color-paper);
	border: var(--pd-border-strong);

	transition: transform var(--pd-motion-fast);
}
```
