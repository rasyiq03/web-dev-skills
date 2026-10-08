# ============================================================
# File      : test_e2e.py
# Deskripsi : Pengujian end-to-end lengkap untuk kopi-senja:
#             validasi brief -> gaps -> pick_direction -> compile_tokens ->
#             scaffold -> penulisan konten minimal & pengisian section ->
#             check (0 error) -> handoff.
# ============================================================

import pytest
from conftest import copy_fixture, next_line, run_script
from lib import io


@pytest.mark.node
def test_kopi_senja_end_to_end(projects_dir):
    # 1. Salin fixture kopi-senja
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])

    # 2. validate_brief
    res_vb = run_script("validate_brief", "kopi-senja")
    assert res_vb.returncode == 0, res_vb.stderr
    assert next_line(res_vb) == "NEXT: run gaps.py"

    # 3. gaps
    res_gap = run_script("gaps", "kopi-senja")
    assert res_gap.returncode == 0, res_gap.stderr
    assert next_line(res_gap) == "NEXT: write directions.yaml (web-design skill)"

    # 4. pick_direction --pick dir-2
    res_pick = run_script("pick_direction", "kopi-senja", "--pick", "dir-2")
    assert res_pick.returncode == 0, res_pick.stderr
    assert next_line(res_pick) == "NEXT: run compile_tokens.py"

    # 5. compile_tokens
    res_tok = run_script("compile_tokens", "kopi-senja")
    assert res_tok.returncode == 0, res_tok.stderr
    assert next_line(res_tok) == "NEXT: run scaffold.py"

    # 6. scaffold
    res_scaf = run_script("scaffold", "kopi-senja")
    assert res_scaf.returncode == 0, res_scaf.stderr

    # 7. Tulis content/id.yaml
    content_dir = proj / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    content_yaml = """pages:
  index:
    title: Kopi Senja — kedai kopi di Bandung
    description: Kedai kopi santai di Bandung untuk mahasiswa dan penikmat kopi.
    sections:
      hero:
        heading: Kopi Senja
        body: Tempat kopi hangat di Bandung untuk kamu yang suka membaca dan diskusi.
        actions:
          - label: Pesan lewat WhatsApp
            href: "https://wa.me/628123456789"
      services:
        heading: Menu Kopi
        items:
          - name: Kopi Susu Senja
            price: "[[ISI: daftar layanan atau menu]]"
      proof:
        heading: Rekam Jejak
        body: Didirikan di Bandung untuk teman-teman mahasiswa.
  tentang:
    title: Tentang Kopi Senja
    description: Perjalanan Kopi Senja menyeduh kopi lokal di Bandung.
    sections:
      story:
        heading: Awal Mula
        body: Berawal dari kecintaan pada seduhan kopi lokal Jawa Barat.
  kontak:
    title: Kontak Kopi Senja
    description: Alamat dan nomor kontak Kopi Senja di Bandung.
    sections:
      contact:
        heading: Hubungi Kami
        body: Kunjungi kedai kami atau sapa kami secara daring.
"""
    io.write_text(content_dir / "id.yaml", content_yaml)

    # 8. Isi konten minimal ke section index.html (menjaga class, id, dan data-pd-pattern)
    site_dir = proj / "site"
    index_file = site_dir / "index.html"
    index_html = io.read_text(index_file)

    # Isi section hero
    hero_replacement = """<section class="pd-section pd-section--hero" id="hero" data-pd-pattern="split-offset">
\t\t\t<h2 class="pd-section__heading">Kopi Senja</h2>
\t\t\t<p class="pd-section__lead">Tempat kopi hangat di Bandung untuk kamu yang suka membaca dan diskusi.</p>
\t\t\t<a class="pd-btn" href="https://wa.me/628123456789">Pesan lewat WhatsApp</a>
\t\t</section>"""
    index_html = index_html.replace(
        '<section class="pd-section pd-section--hero" id="hero" data-pd-pattern="split-offset"></section>',
        hero_replacement,
    )

    # Isi section services
    services_replacement = """<section class="pd-section pd-section--services" id="services" data-pd-pattern="list-with-prices">
\t\t\t<h2 class="pd-section__heading">Menu Kopi</h2>
\t\t\t<ul class="pd-menu-list">
\t\t\t\t<li class="pd-menu-item">Kopi Susu Senja — [[ISI: daftar layanan atau menu]]</li>
\t\t\t</ul>
\t\t</section>"""
    index_html = index_html.replace(
        '<section class="pd-section pd-section--services" id="services" data-pd-pattern="list-with-prices"></section>',
        services_replacement,
    )

    # Isi section proof
    proof_replacement = """<section class="pd-section pd-section--proof" id="proof" data-pd-pattern="facts-ledger">
\t\t\t<h2 class="pd-section__heading">Rekam Jejak</h2>
\t\t\t<p class="pd-section__text">Didirikan di Bandung untuk teman-teman mahasiswa.</p>
\t\t</section>"""
    index_html = index_html.replace(
        '<section class="pd-section pd-section--proof" id="proof" data-pd-pattern="facts-ledger"></section>',
        proof_replacement,
    )

    io.write_text(index_file, index_html)

    # 9. Jalankan check.py
    res_chk = run_script("check", "kopi-senja")
    assert res_chk.returncode == 0, res_chk.stderr
    assert next_line(res_chk) == "NEXT: run handoff.py"

    report_data = io.read_json(proj / "report.json")
    assert report_data["summary"]["errors"] == 0

    # 10. Jalankan handoff.py
    res_handoff = run_script("handoff", "kopi-senja")
    assert res_handoff.returncode == 0, res_handoff.stderr
    assert next_line(res_handoff) == "NEXT: handoff complete"
    assert (proj / "HANDOFF.md").is_file()
    assert (proj / "provenance.json").is_file()
