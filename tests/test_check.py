# ============================================================
# File      : test_check.py
# Deskripsi : Pengujian unit dan CLI untuk check.py: deteksi pelanggaran,
#             perekaman ronde, perbaikan bertahap, dan pemilihan ronde terbaik.
# ============================================================

import pytest
from conftest import copy_fixture, next_line, run_script
from lib import io


@pytest.fixture
def kopi_scaffolded_check(projects_dir):
    """
    Menyiapkan proyek kopi-senja hingga selesai di-scaffold.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    run_script("gaps", "kopi-senja")
    run_script("pick_direction", "kopi-senja", "--pick", "dir-2")
    run_script("compile_tokens", "kopi-senja")
    run_script("scaffold", "kopi-senja")
    return proj


@pytest.mark.node
def test_check_clean_skeleton_passes(kopi_scaffolded_check):
    result = run_script("check", "kopi-senja")
    assert result.returncode == 0, result.stderr
    assert next_line(result) == "NEXT: run handoff.py"

    report_file = kopi_scaffolded_check / "report.json"
    assert report_file.is_file()
    data = io.read_json(report_file)
    assert data["summary"]["errors"] == 0


@pytest.mark.node
def test_check_seeded_violations_and_round_recovery(kopi_scaffolded_check):
    site_dir = kopi_scaffolded_check / "site"

    # 1. Tanam 4 pelanggaran yang disyaratkan spesifikasi:
    # a) hex color di components.css
    comp_file = site_dir / "css" / "components.css"
    comp_text = io.read_text(comp_file)
    comp_text += "\n.pd-dummy { color: #FF0000; }\n"
    io.write_text(comp_file, comp_text)

    # b) & c) href="#" dan section tanpa banner di index.html
    index_file = site_dir / "index.html"
    index_text = io.read_text(index_file)
    # Tambahkan tautan kosong
    index_text = index_text.replace(
        '<header class="pd-header">',
        '<header class="pd-header"><a href="#">Link Kosong</a>',
    )
    # Tambahkan section baru tanpa komentar banner
    index_text = index_text.replace(
        '</main>',
        '<section class="pd-section" id="dummy"></section>\n</main>',
    )
    io.write_text(index_file, index_text)

    # d) if tanpa kurung kurawal di main.js
    main_file = site_dir / "js" / "main.js"
    main_text = io.read_text(main_file)
    main_text += "\nif (true) alert(1);\n"
    io.write_text(main_file, main_text)

    # Ronde 1: Jalankan check.py
    res1 = run_script("check", "kopi-senja")
    assert res1.returncode == 0
    assert next_line(res1) == "NEXT: fix the findings in report.json, then run check.py again"

    report_data1 = io.read_json(kopi_scaffolded_check / "report.json")
    findings1 = report_data1["findings"]
    rules_found = {f["rule"] for f in findings1}

    # Pastikan keempat pelanggaran terdeteksi
    assert any("raw-color" in r or "color-no-hex" in r for r in rules_found)
    assert "empty-link" in rules_found
    assert "banner-missing" in rules_found
    assert any("curly" in r for r in rules_found)

    # Perbaiki pelanggaran: pulihkan site/ dari ronde awal atau bersihkan
    # Bersihkan components.css
    io.write_text(comp_file, comp_text.replace(".pd-dummy { color: #FF0000; }", ""))
    # Bersihkan index.html
    index_clean = index_text.replace('<a href="#">Link Kosong</a>', "").replace(
        '<section class="pd-section" id="dummy"></section>\n', ""
    )
    io.write_text(index_file, index_clean)
    # Bersihkan main.js
    io.write_text(main_file, main_text.replace("if (true) alert(1);", ""))

    # Ronde 2: Jalankan lagi check.py
    res2 = run_script("check", "kopi-senja")
    assert res2.returncode == 0
    assert next_line(res2) == "NEXT: run handoff.py"

    report_data2 = io.read_json(kopi_scaffolded_check / "report.json")
    assert report_data2["summary"]["errors"] == 0
    assert "Ronde terbaik yang dipulihkan" in res2.stdout
