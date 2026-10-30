# ============================================================
# File      : locale_rules.py
# Proyek    : ScaffolDev
# Deskripsi : Pemeriksaan terukur untuk situs berbahasa Indonesia
#             (references/indonesia.md): lang halaman, tombol WhatsApp
#             di hero, format nomor wa.me, berat halaman untuk ponsel,
#             serta format harga dan jam.
# ============================================================

import re

from . import io, paths

# Batas berat satu halaman (HTML + CSS/JS/gambar lokal) untuk ponsel kelas menengah
# dengan data seluler; font Google dan berkas dari luar tidak dihitung
PAGE_BUDGET_KB = 500

HTML_LANG = re.compile(r"<html\b[^>]*\blang=\"([^\"]*)\"", re.IGNORECASE)
LOCAL_REF = re.compile(r"""(?:href|src)="(?!https?:|//|data:|mailto:|tel:|#)([^"?#]+)""")
HERO = re.compile(r"<section\b[^>]*\bid=\"hero\"[^>]*>(.*?)</section>", re.DOTALL | re.IGNORECASE)
WA_LINK = re.compile(r"href=\"(https?://(?:wa\.me|api\.whatsapp\.com)/[^\"]*)\"", re.IGNORECASE)
NON_VISIBLE = re.compile(r"<(script|style)\b.*?</\1>|<!--.*?-->|<[^>]+>", re.DOTALL | re.IGNORECASE)

PRICE_WRONG = re.compile(r"\b(?:Rp\.?\s+\d|IDR\s?\d|Rp\.?\s?\d{1,3}(?:,\d{3})+(?!\d))")
TIME_WRONG = re.compile(r"\b\d{1,2}:\d{2}(?:\s?[AaPp]\.?[Mm]\.?)?\b")


def page_language(rel, languages):
    """
    Menentukan bahasa sebuah halaman dari letaknya.

    I.S. : rel adalah path halaman relatif ke situs; languages dari brief.
    F.S. : Kode bahasa dikembalikan; bahasa kedua dan seterusnya ada di folder <lang>/.
    """
    first = rel.split("/", 1)[0]
    return first if first in languages[1:] else languages[0]


def _finding(rule, level, rel, line, message, fix):
    """
    Menyusun satu temuan dengan bentuk yang sama seperti audit_rules.

    I.S. : Semua argumen terisi.
    F.S. : Dict temuan dikembalikan.
    """
    return {"rule": rule, "category": "design", "level": level, "file": rel, "line": line, "message": message, "fix": fix}


def _line_of(content, index):
    """
    Menghitung nomor baris dari posisi karakter.

    I.S. : index adalah posisi di content.
    F.S. : Nomor baris (mulai 1) dikembalikan.
    """
    return content.count("\n", 0, index) + 1


def _page_weight(site_dir, html_file, content):
    """
    Menjumlahkan berat halaman beserta berkas lokal yang dimuatnya.

    I.S. : html_file ada di site_dir; content adalah isinya.
    F.S. : Berat dalam byte dikembalikan; setiap berkas hanya dihitung sekali.
    """
    seen = {html_file.resolve()}
    total = len(content.encode("utf-8"))
    for ref in LOCAL_REF.findall(content):
        target = (html_file.parent / ref).resolve()
        if target in seen or not target.is_file() or target.suffix == ".html":
            continue
        if site_dir.resolve() not in target.parents:
            continue
        seen.add(target)
        total += target.stat().st_size
    return total


def check_locale(proj_dir, brief, site_type):
    """
    Menjalankan semua pemeriksaan lokal Indonesia pada halaman situs.

    I.S. : proj_dir adalah folder kerja; situs sudah dibangun; brief dan site_type terbaca.
    F.S. : List temuan dikembalikan. lang dan berat halaman berlaku untuk semua situs;
           WhatsApp, harga, dan jam hanya untuk halaman berbahasa Indonesia.
    """
    site_dir = paths.site_dir(proj_dir)
    languages = brief.get("languages") or ["id"]
    wants_whatsapp = "whatsapp" in (site_type.get("facts") or [])
    findings = []

    for html_file in paths.site_files(site_dir, "*.html"):
        rel = html_file.relative_to(site_dir).as_posix()
        if rel.startswith("js/vendor/"):
            continue
        content = io.read_text(html_file)
        lang = page_language(rel, languages)

        # 1. lang sesuai bahasa halaman (pemenggalan kata dan pembaca layar bergantung padanya)
        found = HTML_LANG.search(content)
        if not found or found.group(1).split("-")[0].lower() != lang:
            findings.append(_finding(
                "page-lang", "error", rel, _line_of(content, found.start()) if found else 1,
                f"Atribut lang halaman {found.group(1) if found else '(tidak ada)'!r}, seharusnya {lang!r}.",
                f'Set <html lang="{lang}">.',
            ))

        # 2. Berat halaman
        weight_kb = round(_page_weight(site_dir, html_file, content) / 1024)
        if weight_kb > PAGE_BUDGET_KB:
            findings.append(_finding(
                "page-weight", "warning", rel, 1,
                f"Halaman ini memuat {weight_kb} KB berkas lokal (batas {PAGE_BUDGET_KB} KB untuk ponsel dengan data seluler).",
                "Compress images to WebP at the size they are shown, and add loading=\"lazy\" below the fold.",
            ))

        # 3. Nomor wa.me memakai kode negara tanpa nol, tanda plus, atau tanda hubung
        for link in WA_LINK.finditer(content):
            number = re.sub(r"^https?://(?:wa\.me|api\.whatsapp\.com)/(?:send\?phone=)?", "", link.group(1)).split("?")[0]
            if number.startswith("[[ISI") or re.fullmatch(r"62\d{8,13}", number):
                continue
            findings.append(_finding(
                "wa-number-format", "error", rel, _line_of(content, link.start()),
                f"Tautan WhatsApp {link.group(1)!r} tidak akan membuka chat.",
                "Write the number as https://wa.me/62812... (country code 62, no leading 0, no + or dashes).",
            ))

        if lang != "id":
            continue

        # 4. Tombol WhatsApp di hero beranda
        if wants_whatsapp and rel in ("index.html", f"{lang}/index.html"):
            hero = HERO.search(content)
            # Hero kosong berarti halaman belum dibangun (kerangka scaffold)
            built = hero and re.sub(r"<!--.*?-->", "", hero.group(1), flags=re.DOTALL).strip()
            if built and not WA_LINK.search(hero.group(1)):
                findings.append(_finding(
                    "wa-in-hero", "warning", rel, _line_of(content, hero.start()),
                    "Hero beranda tidak punya tombol WhatsApp, padahal pengunjung biasanya bertanya lewat chat.",
                    'Add a "Chat via WhatsApp" button linking to https://wa.me/62... (or the [[ISI: nomor WhatsApp]] placeholder).',
                ))

        # 5. Format harga dan jam di teks yang terlihat
        text = NON_VISIBLE.sub(" ", content)
        for pattern, rule, fix in (
            (PRICE_WRONG, "id-price-format", "Write prices as Rp25.000 or Rp1,5 juta (no space, dot for thousands)."),
            (TIME_WRONG, "id-time-format", "Write times as 08.00–21.00 WIB (dot, 24-hour, with the time zone)."),
        ):
            sample = pattern.search(text)
            if sample:
                findings.append(_finding(
                    rule, "warning", rel, 1,
                    f"Format tidak lazim untuk pembaca Indonesia: {sample.group(0)!r}.",
                    fix,
                ))

    return findings
