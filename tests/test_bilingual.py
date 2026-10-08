# ============================================================
# File      : test_bilingual.py
# Deskripsi : Pengujian fitur situs dwibahasa:
#             - Scaffolding halaman untuk dua bahasa (id & en)
#             - Paritas angka & placeholder antara content/id.yaml & content/en.yaml
# ============================================================

from conftest import copy_fixture, run_script
from lib import audit_rules, io


def test_bilingual_scaffolding_and_parity(projects_dir):
    """
    Memverifikasi pembuatan struktur halaman dwibahasa dan audit paritas.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])

    # Atur brief untuk mendukung dua bahasa: id dan en
    brief = io.read_yaml(proj / "brief.yaml")
    brief["languages"] = ["id", "en"]
    io.write_yaml(proj / "brief.yaml", brief)

    # Perbarui register di directions.yaml agar mencakup 'en'
    directions = io.read_yaml(proj / "directions.yaml")
    for d in directions["directions"]:
        d["register"]["en"] = "you"
    io.write_yaml(proj / "directions.yaml", directions)

    # 1. Jalankan gaps, compile_tokens & scaffold
    res_gap = run_script("gaps", "kopi-senja")
    assert res_gap.returncode == 0, res_gap.stderr
    res_pick = run_script("pick_direction", "kopi-senja", "--pick", "dir-2")
    assert res_pick.returncode == 0, res_pick.stderr
    res_tok = run_script("compile_tokens", "kopi-senja")
    assert res_tok.returncode == 0, res_tok.stderr
    res_scaf = run_script("scaffold", "kopi-senja")
    assert res_scaf.returncode == 0, res_scaf.stderr

    site_dir = proj / "site"
    assert (site_dir / "index.html").is_file()
    assert (site_dir / "pages" / "tentang.html").is_file()
    assert (site_dir / "en" / "index.html").is_file()
    assert (site_dir / "en" / "pages" / "tentang.html").is_file()

    # Periksa atribut lang di root dan subfolder
    id_html = io.read_text(site_dir / "index.html")
    en_html = io.read_text(site_dir / "en" / "index.html")
    assert '<html lang="id">' in id_html
    assert '<html lang="en">' in en_html

    # 2. Uji paritas dwibahasa ketika data sinkron
    content_dir = proj / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    io.write_text(
        content_dir / "id.yaml",
        "tahun: 2024\nharga: 15000\nkontak: '[[ISI: nomor wa]]'\n",
    )
    io.write_text(
        content_dir / "en.yaml",
        "year: 2024\nprice: 15000\ncontact: '[[ISI: whatsapp number]]'\n",
    )

    findings = audit_rules.check_bilingual_parity(proj, brief)
    assert len(findings) == 0, f"Harusnya lolos paritas dwibahasa, tapi ada: {findings}"

    # 3. Uji paritas dwibahasa mendeteksi ketidaksesuaian angka
    io.write_text(
        content_dir / "en.yaml",
        "year: 2025\nprice: 15000\ncontact: '[[ISI: whatsapp number]]'\n",
    )
    findings_mismatch = audit_rules.check_bilingual_parity(proj, brief)
    rules_hit = {f["rule"] for f in findings_mismatch}
    assert "bilingual-number-mismatch" in rules_hit
