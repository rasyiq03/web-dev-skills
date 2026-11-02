# ============================================================
# File      : test_scaffold.py
# Deskripsi : Pengujian unit dan CLI untuk scaffold.py serta verifikasi
#             bahwa skeleton lolos prettier, stylelint, dan html-validate.
# ============================================================

import shutil
import subprocess
import pytest
from conftest import copy_fixture, next_line, run_script

from lib import io

# Tanpa shell=True: di Linux/macOS shell=True dengan list hanya menjalankan "npx" tanpa argumen
NPX = shutil.which("npx") or "npx"


@pytest.fixture
def kopi_scaffolded(projects_dir):
    """
    Menyiapkan proyek kopi-senja dan mengeksekusi sampai langkah scaffold.py.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    run_script("gaps", "kopi-senja")
    run_script("pick_direction", "kopi-senja", "--pick", "dir-2")
    run_script("compile_tokens", "kopi-senja")
    res = run_script("scaffold", "kopi-senja")
    assert res.returncode == 0, res.stderr
    return proj


def test_scaffold_structure_and_idempotence(kopi_scaffolded):
    site_dir = kopi_scaffolded.parent
    assert (site_dir / "index.html").is_file()
    assert (site_dir / "pages" / "tentang.html").is_file()
    assert (site_dir / "pages" / "kontak.html").is_file()
    assert (site_dir / "css" / "tokens.css").is_file()
    assert (site_dir / "css" / "base.css").is_file()
    assert (site_dir / "js" / "main.js").is_file()
    assert (site_dir / "js" / "api" / "client.js").is_file()

    # Cek penggantian template variabel
    client_js = io.read_text(site_dir / "js" / "api" / "client.js")
    assert "{{project_name}}" not in client_js
    assert "Kopi Senja" in client_js

    # Cek penyimpanan hash di state.yaml
    state = io.load_state(kopi_scaffolded)
    assert "config_hashes" in state
    assert ".prettierrc.json" in state["config_hashes"]
    assert "api_template_hashes" in state

    # Uji idempotensi: jalankan lagi tanpa --force harus gagal
    res_repeat = run_script("scaffold", "kopi-senja")
    assert res_repeat.returncode == 1
    assert "sudah berisi situs" in res_repeat.stdout

    # Jalankan dengan --force harus berhasil
    res_force = run_script("scaffold", "kopi-senja", "--force")
    assert res_force.returncode == 0


@pytest.mark.node
def test_scaffold_skeleton_passes_linters(kopi_scaffolded):
    # 1. npx prettier --check
    # Linter dijalankan dari folder situs; config ada di .ScaffolDev
    site_dir = kopi_scaffolded.parent
    cmd_prettier = [NPX, "prettier", "--check", "--config", ".ScaffolDev/.prettierrc.json", "*.html", "pages/*.html", "css/**/*.css"]
    res_p = subprocess.run(cmd_prettier, cwd=site_dir, capture_output=True, text=True)
    assert res_p.returncode == 0, f"prettier gagal:\n{res_p.stdout}\n{res_p.stderr}"

    # 2. npx stylelint
    cmd_stylelint = [
        NPX,
        "stylelint",
        "--config",
        ".ScaffolDev/.stylelintrc.json",
        "css/**/*.css",
    ]
    res_s = subprocess.run(cmd_stylelint, cwd=site_dir, capture_output=True, text=True)
    assert res_s.returncode == 0, f"stylelint gagal:\n{res_s.stdout}\n{res_s.stderr}"

    # 3. npx html-validate
    cmd_htmlval = [
        NPX,
        "html-validate",
        "--config",
        ".ScaffolDev/.htmlvalidate.json",
        "index.html",
        "pages/*.html",
    ]
    res_h = subprocess.run(cmd_htmlval, cwd=site_dir, capture_output=True, text=True)
    assert res_h.returncode == 0, f"html-validate gagal:\n{res_h.stdout}\n{res_h.stderr}"


def test_base_css_uses_readable_link_color(kopi_scaffolded):
    base = (kopi_scaffolded.parent / "css" / "base.css").read_text(encoding="utf-8")

    assert "color: var(--pd-color-link);" in base
    assert "solid var(--pd-color-link);" in base
    assert "var(--pd-color-accent)" not in base


def test_scaffold_writes_a_stand_in_favicon(kopi_scaffolded):
    site = kopi_scaffolded.parent
    icon = (site / "assets" / "img" / "favicon.svg").read_text(encoding="utf-8")

    assert '>K</text>' in icon
    assert 'fill="#F26B3A"' in icon
    assert '<link rel="icon" href="assets/img/favicon.svg" type="image/svg+xml"' in (site / "index.html").read_text(encoding="utf-8")
    assert 'href="../assets/img/favicon.svg"' in (site / "pages" / "kontak.html").read_text(encoding="utf-8")

    assert run_script("handoff", "kopi-senja").returncode == 0
    assert "`assets/img/favicon.svg` masih sementara" in (kopi_scaffolded / "HANDOFF.md").read_text(encoding="utf-8")
