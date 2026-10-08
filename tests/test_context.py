# ============================================================
# File      : test_context.py
# Deskripsi : Pengujian unit dan CLI untuk context.py.
# ============================================================

from conftest import copy_fixture, next_line, run_script


def test_context_kopi_senja_index(projects_dir):
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    run_script("gaps", "kopi-senja")
    run_script("pick_direction", "kopi-senja", "--pick", "dir-2")
    run_script("compile_tokens", "kopi-senja")

    result = run_script("context", "kopi-senja", "index")
    assert result.returncode == 0, result.stderr
    out = result.stdout

    # Baris-baris format triple linier
    assert "page | index.html | sections:" in out
    assert "d-style-1 | style | neobrutalism" in out
    assert "d-typo-1 | typography |" in out
    assert "section | hero | pattern split-offset" in out
    assert "tokens | --pd-color-ink" in out
    assert "component | button |" in out
    assert "signature |" in out
    assert "placeholders |" in out
    assert "content | content/id.yaml#index" in out
    assert "approx_tokens |" in out

    # Periksa batas token (< 1500)
    chars = len(out)
    tokens = chars / 4
    assert tokens < 1500

    assert next_line(result) == "NEXT: build index.html (see skills/web-build/SKILL.md step 6)"


def test_context_invalid_page_exits_1(projects_dir):
    copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    run_script("gaps", "kopi-senja")
    run_script("pick_direction", "kopi-senja", "--pick", "dir-2")

    result = run_script("context", "kopi-senja", "nonexistent")
    assert result.returncode == 1
    assert "tidak ditemukan" in result.stdout
