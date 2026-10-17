# ============================================================
# File      : test_explain.py
# Deskripsi : Pengujian EXPLAIN.html: isi tiap bagian, bahasa, status check,
#             halaman mandiri tanpa jaringan, determinisme, dan peloloskan HTML.
# ============================================================

import json
import re

import pytest
from conftest import copy_fixture, next_line, run_script

from lib import explain


@pytest.fixture
def kopi_tokens(projects_dir):
    """
    Menyiapkan kopi-senja sampai token tersusun.

    I.S. : projects_dir kosong.
    F.S. : gaps, decisions, dan tokens kopi-senja ada; path folder proyek dikembalikan.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])

    for args in (("gaps",), ("pick_direction", "--pick", "dir-2"), ("compile_tokens",)):
        assert run_script(args[0], "kopi-senja", *args[1:]).returncode == 0

    return proj


def test_cli_writes_explain_page(kopi_tokens):
    result = run_script("explain", "kopi-senja")

    assert result.returncode == 0, result.stdout
    assert (kopi_tokens / "EXPLAIN.html").is_file()
    assert next_line(result) == "NEXT: tell the user where EXPLAIN.html is and what it shows"


def test_page_has_every_section_in_indonesian(kopi_tokens):
    page = explain.build_html(kopi_tokens)

    assert '<html lang="id">' in page
    for heading in ("Langkah kerja", "Pembagian peran", "Keputusan desain", "Graf konteks",
                    "Yang masih harus diisi", "Hasil pemeriksaan", "Uji pemahaman"):
        assert f">{heading}</h2>" in page, heading

    assert "Palet warna: warm-paper" in page
    assert "warm-paper · 24% · dipilih" in page
    assert "ink-on-cream · 34%" in page
    assert "[[ISI: nomor WhatsApp]]" in page
    assert "Kenapa tata letak ini dipilih untuk situs ini?" in page


def test_page_follows_brief_language(kopi_tokens):
    brief = kopi_tokens / "brief.yaml"
    brief.write_text(brief.read_text(encoding="utf-8").replace("languages: [id]", "languages: [en]"), encoding="utf-8")

    page = explain.build_html(kopi_tokens)

    assert '<html lang="en">' in page
    assert ">Design decisions</h2>" in page
    assert "Requirements / gaps" in page


def test_check_status_comes_from_report(kopi_tokens):
    report_data = {
        "summary": {"errors": 1, "warnings": 0, "tfs_auto": 0.92},
        "findings": [{"rule": "constraint-c-contrast-body", "level": "error", "message": "kontras rendah"}],
    }
    (kopi_tokens / "report.json").write_text(json.dumps(report_data), encoding="utf-8")

    page = explain.build_html(kopi_tokens)

    assert re.search(r"c-contrast-body</code> <span class=\"bad\">✗ gagal", page)
    assert re.search(r"c-contrast-accent</code> <span class=\"ok\">✓ lolos", page)
    assert "1 error · 0 peringatan · 92% aturan desain terpenuhi" in page


def test_before_check_status_is_not_checked(kopi_tokens):
    page = explain.build_html(kopi_tokens)

    assert "c-contrast-body</code> <span>belum diperiksa" in page
    assert "Situs belum diperiksa" in page


def test_page_is_self_contained(kopi_tokens):
    page = explain.build_html(kopi_tokens)

    assert not re.search(r"(src|href)=[\"']?(https?:)?//", page)
    assert "<link" not in page
    assert "@import" not in page


def test_graph_data_matches_svg(kopi_tokens):
    page = explain.build_html(kopi_tokens)
    payload = re.search(r'<script type="application/json" id="pd-graph-data">(.*?)</script>', page).group(1)
    data = json.loads(payload)
    drawn = set(re.findall(r'<g data-id="([^"]+)"', page))

    assert "token:color.accent" in drawn
    assert "page:index" not in drawn
    assert ["d-palette-1", "req-audience", "based_on"] in data["edges"]
    assert "token:color.chart-1" in drawn
    assert "token:size.step-0" not in drawn
    assert re.search(r"\d+ token lain tidak terkait keputusan", page)


def test_page_is_deterministic(kopi_tokens):
    assert explain.build_html(kopi_tokens) == explain.build_html(kopi_tokens)


def test_text_from_brief_is_escaped(kopi_tokens):
    brief = kopi_tokens / "brief.yaml"
    text = brief.read_text(encoding="utf-8").replace("value: Kopi Senja", 'value: "Kopi </script><b>Senja"')
    brief.write_text(text, encoding="utf-8")

    page = explain.build_html(kopi_tokens)

    assert "Kopi &lt;/script&gt;&lt;b&gt;Senja" in page
    assert "</script><b>" not in page


def test_page_works_with_brief_only(kopi):
    page = explain.build_html(kopi)

    assert "Langkah kerja" in page
    assert "Keputusan desain" not in page
