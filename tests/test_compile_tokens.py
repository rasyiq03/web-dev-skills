# ============================================================
# File      : test_compile_tokens.py
# Deskripsi : Pengujian unit dan CLI untuk compile_tokens.py.
# ============================================================

import shutil
import subprocess
import pytest
from conftest import copy_fixture, next_line, run_script

from lib import io

# Tanpa shell=True: di Linux/macOS shell=True dengan list hanya menjalankan "npx" tanpa argumen
NPX = shutil.which("npx") or "npx"


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
    cmd = [NPX, "stylelint", "--config", "config/.stylelintrc.json", str(css_file)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"stylelint gagal pada tokens.css:\n{res.stdout}\n{res.stderr}"


def test_every_advertised_token_exists_in_tokens_css(kopi_dir2):
    # Nama token yang dicetak context harus persis variabel yang ada di tokens.css
    import re

    from lib import graph

    for name in ("gaps", "pick_direction"):
        args = ("--pick", "dir-2") if name == "pick_direction" else ()
        assert run_script(name, "kopi-senja", *args).returncode == 0
    assert run_script("compile_tokens", "kopi-senja").returncode == 0

    defined = set(re.findall(r"(--pd-[a-z0-9-]+):", (kopi_dir2 / "tokens.css").read_text(encoding="utf-8")))
    advertised = {n["label"] for n in graph.build(kopi_dir2)["nodes"] if n["type"] == "token"}
    pattern = re.compile(r"^--pd-[a-z0-9]+(-[a-z0-9]+)*$")

    assert advertised <= defined, sorted(advertised - defined)
    assert all(pattern.match(name) for name in defined), [n for n in defined if not pattern.match(n)]


def test_compile_after_scaffold_updates_the_site(kopi_dir2):
    assert run_script("compile_tokens", "kopi-senja").returncode == 0
    assert run_script("scaffold", "kopi-senja").returncode == 0
    site_css = kopi_dir2.parent / "css" / "tokens.css"
    site_css.write_text("/* lama */\n", encoding="utf-8")

    result = run_script("compile_tokens", "kopi-senja")

    assert next_line(result) == "NEXT: run check.py"
    assert site_css.read_bytes() == (kopi_dir2 / "tokens.css").read_bytes()
