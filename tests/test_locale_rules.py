# ============================================================
# File      : test_locale_rules.py
# Deskripsi : Pengujian pemeriksaan lokal Indonesia di check.py: lang
#             halaman, tombol WhatsApp di hero, format nomor wa.me, berat
#             halaman, serta format harga dan jam.
# ============================================================

from conftest import copy_fixture, run_script
from lib import io, locale_rules, project


def built_kopi(projects_dir):
    """
    Menyiapkan kopi-senja sampai scaffold, lalu mengembalikan folder kerja dan beranda.

    I.S. : PD_PROJECTS_DIR menunjuk projects_dir.
    F.S. : (work, index.html, brief, site_type) dikembalikan.
    """
    work = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    for args in (("gaps",), ("pick_direction", "--pick", "dir-2"), ("compile_tokens",), ("scaffold",)):
        assert run_script(args[0], "kopi-senja", *args[1:]).returncode == 0
    brief = io.read_yaml(work / "brief.yaml")
    return work, work.parent / "index.html", brief, project.load_site_type(brief["site_type"])


def fill_hero(index, html):
    text = index.read_text(encoding="utf-8")
    start = text.index('id="hero"')
    end = text.index("</section>", start)
    close = text.index(">", start) + 1
    index.write_text(text[:close] + html + text[end:], encoding="utf-8")


def rules(work, brief, site_type):
    return {(f["rule"], f["file"]) for f in locale_rules.check_locale(work, brief, site_type)}


def test_hero_without_whatsapp_is_flagged_and_a_placeholder_link_passes(projects_dir):
    work, index, brief, site_type = built_kopi(projects_dir)
    assert ("wa-in-hero", "index.html") not in rules(work, brief, site_type)  # kerangka kosong

    fill_hero(index, "<h1>Kopi Senja</h1>")
    assert ("wa-in-hero", "index.html") in rules(work, brief, site_type)

    fill_hero(index, '<a href="https://wa.me/[[ISI: nomor WhatsApp]]">Chat via WhatsApp</a>')
    assert not {r for r, _ in rules(work, brief, site_type)} & {"wa-in-hero", "wa-number-format"}


def test_whatsapp_numbers_need_the_country_code(projects_dir):
    work, index, brief, site_type = built_kopi(projects_dir)

    fill_hero(index, '<a href="https://wa.me/0812-3456-7890">Chat</a>')
    assert ("wa-number-format", "index.html") in rules(work, brief, site_type)

    fill_hero(index, '<a href="https://wa.me/6281234567890?text=Halo%20Kak">Chat</a>')
    assert ("wa-number-format", "index.html") not in rules(work, brief, site_type)


def test_page_lang_must_match_the_page_language(projects_dir):
    work, index, brief, site_type = built_kopi(projects_dir)
    assert ("page-lang", "index.html") not in rules(work, brief, site_type)

    index.write_text(index.read_text(encoding="utf-8").replace('<html lang="id"', '<html lang="en"'), encoding="utf-8")
    assert ("page-lang", "index.html") in rules(work, brief, site_type)
    assert locale_rules.page_language("en/pages/kontak.html", ["id", "en"]) == "en"
    assert locale_rules.page_language("pages/kontak.html", ["id", "en"]) == "id"


def test_indonesian_price_and_time_formats(projects_dir):
    work, index, brief, site_type = built_kopi(projects_dir)

    fill_hero(index, '<a href="https://wa.me/6281234567890">Chat</a><p>Kopi susu Rp25.000, buka 08.00–21.00 WIB</p>')
    found = {r for r, _ in rules(work, brief, site_type)}
    assert not found & {"id-price-format", "id-time-format"}

    fill_hero(index, '<a href="https://wa.me/6281234567890">Chat</a><p>Kopi susu Rp 25,000, buka 8:00 AM</p>')
    found = {r for r, _ in rules(work, brief, site_type)}
    assert {"id-price-format", "id-time-format"} <= found


def test_heavy_page_is_flagged(projects_dir):
    work, index, brief, site_type = built_kopi(projects_dir)
    assert ("page-weight", "index.html") not in rules(work, brief, site_type)

    photo = index.parent / "assets" / "img" / "hero.jpg"
    photo.write_bytes(b"\0" * (locale_rules.PAGE_BUDGET_KB + 50) * 1024)
    fill_hero(index, '<img src="assets/img/hero.jpg" alt="Kopi" width="800" height="600">')
    assert ("page-weight", "index.html") in rules(work, brief, site_type)


def test_mock_label_is_needed_only_when_endpoints_exist(projects_dir):
    from lib import audit_rules

    work, index, brief, site_type = built_kopi(projects_dir)
    catalog = project.load_site_type("umkm-catalog")  # beranda punya seksi data "featured"
    index.write_text(index.read_text(encoding="utf-8").replace("data-pd-mock-label", "data-x"), encoding="utf-8")

    # Template endpoints.js hanya berisi contoh di komentar: bukan endpoint, tak perlu label
    rules_found = {f["rule"] for f in audit_rules.check_data_layer(work, catalog)}
    assert not rules_found & {"mock-file-invalid", "mock-label-missing"}

    endpoints = index.parent / "js" / "api" / "endpoints.js"
    endpoints.write_text(endpoints.read_text(encoding="utf-8").replace(
        "export const ENDPOINTS = {", "export const ENDPOINTS = {\n\tproducts: { method: 'GET', path: '/products', mock: 'products' },"),
        encoding="utf-8")
    rules_found = {f["rule"] for f in audit_rules.check_data_layer(work, catalog)}
    assert {"mock-file-invalid", "mock-label-missing"} <= rules_found


def test_bilingual_copy_with_a_split_sentence_is_flagged(tmp_path):
    from lib import audit_rules

    work = tmp_path / ".ScaffolDev"
    (work / "content").mkdir(parents=True)
    (work / "content" / "id.yaml").write_text(
        "pages:\n  index:\n    sections:\n      story:\n        body: [Di Yogyakarta, Anda bisa membatik.]\n", encoding="utf-8")
    (work / "content" / "en.yaml").write_text(
        "pages:\n  index:\n    sections:\n      story:\n        body: [In Yogyakarta you can draw batik.]\n", encoding="utf-8")

    findings = audit_rules.check_bilingual_parity(work, {"languages": ["id", "en"]})

    assert [f["message"] for f in findings if f["rule"] == "bilingual-structure-mismatch"] == [
        "Struktur naskah id dan en berbeda di pages.index.sections.story.body (2 lawan 1 butir)."]
