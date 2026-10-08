# ============================================================
# File      : test_compile_tokens.py
# Deskripsi : Pengujian unit dan CLI untuk compile_tokens.py.
# ============================================================

import subprocess
import pytest
from conftest import copy_fixture, next_line, run_script
from lib import io


@pytest.fixture
def kopi_dir2(projects_dir):
    """
    Menyiapkan proyek kopi-senja dengan dir-2 terpilih.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    run_script("gaps", "kopi-senja")
    run_script("pick_direction", "kopi-senja", "--pick", "dir-2")
    return proj


def test_compile_tokens_dir2_acceptance(kopi_dir2):
    result = run_script("compile_tokens", "kopi-senja")
    assert result.returncode == 0, result.stderr
    assert next_line(result) == "NEXT: run scaffold.py"

    css_file = kopi_dir2 / "tokens.css"
    assert css_file.is_file()
    css_content = io.read_text(css_file)

    # Kriteria penerimaan dari spesifikasi
    assert "--pd-color-paper: #F4EBDD;" in css_content
    assert "--pd-font-display: 'Archivo Black', sans-serif;" in css_content
    assert "--pd-color-chart-1: #F26B3A;" in css_content
    assert "--pd-color-chart-2:" in css_content
    assert "--pd-color-positive:" in css_content

    # Cek file fonts.html dan tokens.json
    fonts_file = kopi_dir2 / "fonts.html"
    assert fonts_file.is_file()
    fonts_content = io.read_text(fonts_file)
    assert "fonts.googleapis.com" in fonts_content
    assert "Archivo+Black" in fonts_content

    tokens_json = kopi_dir2 / "tokens.json"
    assert tokens_json.is_file()
    data = io.read_json(tokens_json)
    assert "color" in data
    assert "font" in data
    assert "size" in data


def test_compile_tokens_low_contrast_rejection(kopi_dir2):
    # Buat arah kustom dengan kontras rendah (#777777 di atas #888888)
    dirs_file = kopi_dir2 / "directions.yaml"
    dirs_data = io.read_yaml(dirs_file)
    dir_entry = dirs_data["directions"][1]  # dir-2
    dir_entry["palette"] = "custom"
    dir_entry["colors"] = {
        "ink": "#777777",
        "paper": "#888888",
        "accent": "#F26B3A",
        "muted": "#666666",
        "accent-ink": "#FFFFFF",
    }
    io.write_yaml(dirs_file, dirs_data)

    # Jalankan ulang pick_direction untuk memperbarui decisions
    run_script("pick_direction", "kopi-senja", "--pick", "dir-2")

    result = run_script("compile_tokens", "kopi-senja")
    # Harus keluar dengan kode 2 (EXIT_CHECK_FAILED)
    assert result.returncode == 2
    assert "Kontras" in result.stdout or "WCAG" in result.stdout


@pytest.mark.node
def test_tokens_css_passes_stylelint(kopi_dir2):
    run_script("compile_tokens", "kopi-senja")
    css_file = kopi_dir2 / "tokens.css"

    # Jalankan stylelint pada tokens.css
    cmd = ["npx", "stylelint", "--config", "config/.stylelintrc.json", str(css_file)]
    res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    assert res.returncode == 0, f"stylelint gagal pada tokens.css:\n{res.stdout}\n{res.stderr}"
