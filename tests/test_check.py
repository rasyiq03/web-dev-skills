# ============================================================
# File      : test_check.py
# Deskripsi : Pengujian unit dan CLI untuk check.py: deteksi pelanggaran,
#             perekaman ronde, perbaikan bertahap, dan pemilihan ronde terbaik.
# ============================================================

import sys
from pathlib import Path

import pytest
from conftest import REPO, add_git_folder, copy_fixture, next_line, run_script
from lib import io


def scaffold_kopi(projects_dir):
    """
    Menyiapkan proyek kopi-senja di projects_dir hingga selesai di-scaffold.

    I.S. : PD_PROJECTS_DIR sudah menunjuk projects_dir.
    F.S. : projects_dir/kopi-senja/site/ berisi skeleton; path folder proyek dikembalikan.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    run_script("gaps", "kopi-senja")
    run_script("pick_direction", "kopi-senja", "--pick", "dir-2")
    run_script("compile_tokens", "kopi-senja")
    run_script("scaffold", "kopi-senja")
    return proj


def seed_lint_violations(proj):
    """
    Menanam satu pelanggaran ESLint dan satu pelanggaran stylelint yang tidak bisa di-fix otomatis.

    I.S. : proj sudah di-scaffold.
    F.S. : main.js memuat if tanpa kurung kurawal; components.css memuat kelas non-BEM.
    """
    main_file = proj / "site" / "js" / "main.js"
    io.write_text(main_file, io.read_text(main_file) + "\nif (true) alert(1);\n")
    comp_file = proj / "site" / "css" / "components.css"
    io.write_text(comp_file, io.read_text(comp_file) + "\n.Bad {\n\tmargin: 0;\n}\n")


def lint_rules(proj):
    """
    Mengambil id aturan dari semua temuan report.json.

    I.S. : check.py sudah dijalankan untuk proj.
    F.S. : Set id aturan dikembalikan.
    """
    return {f["rule"] for f in io.read_json(proj / "report.json")["findings"]}


@pytest.fixture
def kopi_scaffolded_check(projects_dir):
    """
    Menyiapkan proyek kopi-senja di dalam repo hingga selesai di-scaffold.
    """
    return scaffold_kopi(projects_dir)


@pytest.fixture
def kopi_outside_repo(tmp_path, monkeypatch):
    """
    Menyiapkan proyek kopi-senja di folder di luar repo hingga selesai di-scaffold.

    I.S. : tmp_path pytest berada di luar repo (folder temp sistem).
    F.S. : PD_PROJECTS_DIR menunjuk tmp_path; path folder proyek dikembalikan.
    """
    assert not tmp_path.resolve().is_relative_to(REPO)
    monkeypatch.setenv("PD_PROJECTS_DIR", str(tmp_path))
    monkeypatch.setenv("PD_DATE", "2026-10-08")
    return scaffold_kopi(tmp_path)


@pytest.mark.node
def test_check_reports_stylelint_findings(kopi_scaffolded_check):
    seed_lint_violations(kopi_scaffolded_check)

    run_script("check", "kopi-senja")

    assert "selector-class-pattern" in lint_rules(kopi_scaffolded_check)


@pytest.mark.node
def test_check_runs_linters_for_project_outside_repo(kopi_outside_repo):
    seed_lint_violations(kopi_outside_repo)

    run_script("check", "kopi-senja")

    rules = lint_rules(kopi_outside_repo)
    assert "curly" in rules
    assert "selector-class-pattern" in rules
    assert "tool-failed" not in rules


@pytest.mark.node
def test_check_ignores_git_folder_in_site(kopi_scaffolded_check):
    add_git_folder(kopi_scaffolded_check / "site")

    result = run_script("check", "kopi-senja")

    assert result.returncode == 0, result.stderr
    assert next_line(result) == "NEXT: run handoff.py"
    assert not (kopi_scaffolded_check / "rounds" / "1" / "site" / ".git").exists()


@pytest.mark.node
def test_check_reports_failed_tools_as_errors(kopi_scaffolded_check, monkeypatch):
    # PATH hanya berisi folder Python: node tidak bisa ditemukan sama sekali
    monkeypatch.setenv("PATH", str(Path(sys.executable).parent))

    result = run_script("check", "kopi-senja")

    assert next_line(result) == "NEXT: fix the findings in report.json, then run check.py again"
    data = io.read_json(kopi_scaffolded_check / "report.json")
    failed = [f for f in data["findings"] if f["rule"] == "tool-failed"]
    assert {f["level"] for f in failed} == {"error"}
    messages = " ".join(f["message"] for f in failed)
    for tool in ("prettier", "eslint", "stylelint", "html-validate"):
        assert tool in messages
    assert data["summary"]["errors"] >= 4


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
