# ============================================================
# File      : test_scaffold.py
# Deskripsi : Pengujian unit dan CLI untuk scaffold.py serta verifikasi
#             bahwa skeleton lolos prettier, stylelint, dan html-validate.
# ============================================================

import subprocess
import pytest
from conftest import copy_fixture, next_line, run_script
from lib import io


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
    site_dir = kopi_scaffolded / "site"
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
    assert "sudah berisi file" in res_repeat.stdout

    # Jalankan dengan --force harus berhasil
    res_force = run_script("scaffold", "kopi-senja", "--force")
    assert res_force.returncode == 0


@pytest.mark.node
def test_scaffold_skeleton_passes_linters(kopi_scaffolded):
    # 1. npx prettier --check
    cmd_prettier = ["npx", "prettier", "--check", "site/**/*.{html,css}"]
    res_p = subprocess.run(cmd_prettier, cwd=kopi_scaffolded, capture_output=True, text=True, shell=True)
    assert res_p.returncode == 0, f"prettier gagal:\n{res_p.stdout}\n{res_p.stderr}"

    # 2. npx stylelint
    cmd_stylelint = [
        "npx",
        "stylelint",
        "--config",
        ".stylelintrc.json",
        "site/css/**/*.css",
    ]
    res_s = subprocess.run(cmd_stylelint, cwd=kopi_scaffolded, capture_output=True, text=True, shell=True)
    assert res_s.returncode == 0, f"stylelint gagal:\n{res_s.stdout}\n{res_s.stderr}"

    # 3. npx html-validate
    cmd_htmlval = [
        "npx",
        "html-validate",
        "--config",
        ".htmlvalidate.json",
        "site/**/*.html",
    ]
    res_h = subprocess.run(cmd_htmlval, cwd=kopi_scaffolded, capture_output=True, text=True, shell=True)
    assert res_h.returncode == 0, f"html-validate gagal:\n{res_h.stdout}\n{res_h.stderr}"
