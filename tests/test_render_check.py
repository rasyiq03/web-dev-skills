# ============================================================
# File      : test_render_check.py
# Deskripsi : Pengujian tools/render_check.py: metrik kemiripan (EMD warna,
#             tree edit distance) dan pemeriksaan di browser sungguhan
#             (axe-core, gulir menyamping di 390 px, error konsol).
# ============================================================

import sys

import pytest
from conftest import REPO, copy_fixture, fill_empty_sections, run_script

sys.path.insert(0, str(REPO / "tools" / "render"))
sys.path.insert(0, str(REPO / "tools"))

import metrics  # noqa: E402

from lib import io  # noqa: E402


def node(label, *children):
    return [label, list(children)]


def test_tree_edit_distance_matches_the_zhang_shasha_example():
    # Contoh dari makalah Zhang dan Shasha (1989): jaraknya 2
    first = [node("f", node("d", node("a"), node("c", node("b"))), node("e"))]
    second = [node("f", node("c", node("d", node("a"), node("b"))), node("e"))]

    assert metrics.tree_edit_distance(first, second) == 2
    assert metrics.tree_edit_distance(first, first) == 0
    assert metrics.layout_distance(first, first) == 0


def test_color_distance_is_zero_for_the_same_palette_and_grows_with_difference():
    light = metrics.color_histogram([[250, 245, 235, 10], [40, 30, 20, 2]])
    dark = metrics.color_histogram([[20, 20, 25, 10], [230, 230, 230, 2]])
    almost = metrics.color_histogram([[248, 244, 236, 10], [45, 32, 22, 2]])

    assert metrics.color_distance(light, light) == 0
    assert metrics.color_distance(light, almost) < metrics.color_distance(light, dark)
    assert metrics.color_distance(light, dark) > 50


@pytest.mark.network
def test_render_check_finds_overflow_contrast_and_script_errors(projects_dir):
    import render_check

    try:
        render_check.find_browser()
    except Exception:
        pytest.skip("Chrome atau Chromium tidak terpasang")

    work = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    for args in (("gaps",), ("pick_direction", "--pick", "dir-2"), ("compile_tokens",), ("scaffold",)):
        assert run_script(args[0], "kopi-senja", *args[1:]).returncode == 0
    fill_empty_sections(work.parent)

    index = work.parent / "index.html"
    index.write_text(index.read_text(encoding="utf-8").replace(
        "</main>", '<p style="width: 600px; color: #ddd">Pertanggungjawaban</p></main>'), encoding="utf-8")
    (work.parent / "js" / "main.js").write_text("throw new Error('uji');\n", encoding="utf-8")

    result = run_script("render_check", "kopi-senja", script_dir=REPO / "tools")

    assert result.returncode == 2, result.stdout + result.stderr
    rules = {(f["rule"], f["file"]) for f in io.read_json(work / "report.json")["findings"]}
    assert ("horizontal-overflow", "index.html") in rules
    assert ("axe-color-contrast", "index.html") in rules
    assert ("console-error", "index.html") in rules
    assert (work / "render" / "index-390.png").is_file()
    assert "color" in io.read_json(work / "render.json")
