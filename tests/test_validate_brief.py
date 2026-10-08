# ============================================================
# File      : test_validate_brief.py
# Deskripsi : Pengujian unit dan CLI untuk validate_brief.py.
# ============================================================

import pytest
from conftest import next_line, run_script
from lib import io


def test_validate_brief_kopi_senja_passes(kopi):
    result = run_script("validate_brief", "kopi-senja")
    assert result.returncode == 0, result.stderr
    assert "Brief sah untuk proyek 'kopi-senja'" in result.stdout
    assert "req-business.name" in result.stdout
    assert next_line(result) == "NEXT: run gaps.py"


def test_validate_brief_missing_required_field_exits_3(kopi):
    brief_file = kopi / "brief.yaml"
    brief = io.read_yaml(brief_file)

    # Ubah field wajib (business.location) menjadi unknown
    brief["business"]["location"] = {"value": "unknown", "source": "unknown"}
    io.write_yaml(brief_file, brief)

    result = run_script("validate_brief", "kopi-senja")
    assert result.returncode == 3
    # Harus mencetak pertanyaan atau prompt untuk field tersebut
    assert "business.location" in result.stdout
    assert next_line(result) == "NEXT: answer the questions and update brief.yaml"


def test_validate_brief_stated_unknown_exits_1(kopi):
    brief_file = kopi / "brief.yaml"
    brief = io.read_yaml(brief_file)

    # Sumber dinyatakan stated, tetapi nilainya 'unknown' (melanggar skema)
    brief["business"]["name"] = {"value": "unknown", "source": "stated"}
    io.write_yaml(brief_file, brief)

    result = run_script("validate_brief", "kopi-senja")
    assert result.returncode == 1
    assert "Galat skema pada brief.yaml" in result.stdout


def test_validate_brief_slug_mismatch_exits_1(kopi):
    brief_file = kopi / "brief.yaml"
    brief = io.read_yaml(brief_file)
    brief["slug"] = "beda-slug"
    io.write_yaml(brief_file, brief)

    result = run_script("validate_brief", "kopi-senja")
    assert result.returncode == 1
    assert "tidak cocok dengan folder" in result.stdout
