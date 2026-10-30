# Designing for Indonesia

Read this when the brief's languages include `id` or the business is in Indonesia. It
applies to the design direction (web-design), the copy (step 5), the build (step 6), and
how you talk to the user. Indonesia is not one culture: use the details the brief gives
(city, region, community) and never fill gaps with stereotypes.

## How you work with the user

- **Santun tapi jujur.** Be polite, and still name every problem plainly. Never hide a
  failed check or a missing fact to keep the mood pleasant (no *asal bapak senang*).
  Say what is wrong, why it matters, and what you suggest, in that order.
- **Usul, bukan vonis.** Offer choices as proposals: "Saran saya …, karena …". When you
  disagree with the user, give the reason and the alternative, then follow their call.
- **Plain Indonesian.** Short sentences (about 20 words at most), everyday words, standard
  spelling (EYD V). Explain a technical term once, the first time it appears:
  "token warna (nilai warna yang dipakai ulang di seluruh situs)". Prefer Indonesian words
  that developers actually use (*halaman*, *tombol*, *warna utama*); keep English only for
  names of tools and files.
- **Address the user** with "Anda" unless they write casually with "aku" or "kamu"; then
  match them.

## Who visits the site

- **Phone first, modest data.** Most visitors use a mid-range Android phone on mobile
  data. Design at 360 px first. Keep the first load light: compressed WebP images with
  `width` and `height`, `loading="lazy"` below the fold, no autoplay video, no web font
  beyond the pairing's three families, motion `low` unless the brief asks for more.
- **WhatsApp is the front door.** The main call to action for a business is usually a chat:
  a `https://wa.me/62…` link with a prefilled message ("Halo Kak, saya mau tanya …"). Put
  it in the hero, keep a sticky or repeated button on long pages, and label it with the
  action: "Chat via WhatsApp", "Pesan lewat WhatsApp".
- **Other channels people expect** (only when the brief gives them): Instagram and TikTok
  links, a Tokopedia or Shopee shop, a Google Maps link.
- **Directions by landmark.** People find places by *patokan*: "dekat Masjid Raya",
  "seberang kampus". Show the address with its landmark when stated, plus a map link.

## Trust signals

Visitors check whether a business is real before they chat. Use these only when the brief
states them; otherwise each becomes a placeholder, never an invented claim:

- registrations and certificates: NIB, P-IRT, BPOM, halal certificate;
- real photos of the place, the owner, or the product;
- "Sejak <tahun>", the number of branches, payment options (QRIS, transfer bank, COD);
- testimonials and reviews, which stay `[[ISI: testimoni pelanggan]]` until supplied.

## Formats

| Thing | Write | Not |
| --- | --- | --- |
| Price | Rp25.000 · Rp1,5 juta | Rp 25,000 · IDR 25000 |
| Date | 17 Oktober 2026 | 10/17/2026 |
| Time | 08.00–21.00 WIB | 8:00 AM–9:00 PM |
| Phone | 0812-3456-7890 (display), `62812…` (link) | +1-style grouping |
| Numbers | 1.250 pesanan · 12,5% | 1,250 · 12.5% |

Use `Intl.NumberFormat('id-ID')` and `Intl.DateTimeFormat('id-ID')` in scripts, and name
the time zone (WIB, WITA, WIT) whenever hours appear.

## Visual culture

- **Local identity comes from the brief, not from ornament.** A batik border, wayang
  silhouette, or red-and-white scheme on a site that has nothing to do with them is a
  cliché. Use a cultural motif only when the business itself carries it (a batik shop, a
  regional restaurant, a cultural event) and then name the specific motif or region.
- **No assumptions about religion or ethnicity.** Do not add Ramadan greetings, Friday
  closing times, or halal labels unless stated. Photos and illustrations show people
  dressed modestly and plausibly for the place.
- **Long words.** Indonesian words run long (*pertanggungjawaban*, *keanggotaan*). Avoid
  tight letter spacing and all-caps on buttons, let labels wrap, and keep
  `hyphens: auto` working by leaving `lang="id"` on the page.
- **Warm and friendly reads as trustworthy** for most small businesses; government,
  health, finance, and education lean formal ("Anda", fuller sentences, calmer colors).
  Let the brief's audience decide, as `copy-id.md` says for register.

## What check.py verifies

`check.py` reports these from the built pages, so fix them like any other finding:
`page-lang` (each page's `lang`), `wa-number-format` (`https://wa.me/62…`), `wa-in-hero`
(a WhatsApp button in the home page hero when the site type takes WhatsApp), `page-weight`
(500 KB of local files per page), and `id-price-format` / `id-time-format` (the table above).
