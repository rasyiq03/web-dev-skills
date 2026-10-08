# ============================================================
# File      : test_lib.py
# Deskripsi : Pengujian unit modul bersama lib/ (paths, io, report,
#             labels, project).
# ============================================================

import pytest
from lib import io, labels, paths, project, report


def test_paths_slug_validation():
    assert paths.is_valid_slug("kopi-senja")
    assert paths.is_valid_slug("my-site-123")
    assert not paths.is_valid_slug("Kopi_Senja")
    assert not paths.is_valid_slug("-kopi")
    assert not paths.is_valid_slug("kopi-")
    assert not paths.is_valid_slug("")


def test_paths_page_file():
    assert paths.page_file("index") == "index.html"
    assert paths.page_file("tentang") == "pages/tentang.html"
    assert paths.page_file("kontak") == "pages/kontak.html"


def test_paths_today(monkeypatch):
    monkeypatch.setenv("PD_DATE", "2026-10-08")
    assert paths.today() == "2026-10-08"
    assert paths.today({"created": "2025-01-01"}) == "2026-10-08"

    monkeypatch.delenv("PD_DATE", raising=False)
    assert paths.today({"created": "2025-01-01"}) == "2025-01-01"


def test_io_deterministic_text_and_lf(tmp_path):
    f = tmp_path / "test.txt"
    io.write_text(f, "line1\r\nline2\n")
    content = io.read_text(f)
    assert content == "line1\nline2\n"
    # Byte check: strictly LF (\n), no \r
    assert b"\r" not in f.read_bytes()


def test_io_yaml_and_json(tmp_path):
    data = {"b": 2, "a": 1, "c": [3, 4]}
    f_json = tmp_path / "test.json"
    io.write_json(f_json, data)
    assert io.read_json(f_json) == data

    f_yaml = tmp_path / "test.yaml"
    io.write_yaml(f_yaml, data, header="Uji coba")
    loaded = io.read_yaml(f_yaml)
    assert loaded == data
    # Pastikan baris header ada
    assert io.read_text(f_yaml).startswith("# Uji coba\n")


def test_io_yaml_scalar_quoting():
    assert io.yaml_scalar("plain") == "plain"
    assert io.yaml_scalar("with: colon") == '"with: colon"'
    assert io.yaml_scalar("with=equals") == '"with=equals"'
    assert io.yaml_scalar("true") == '"true"'
    assert io.yaml_scalar("123") == '"123"'
    assert io.yaml_flow_list(["a", "b", "c: d"]) == '[a, b, "c: d"]'
    assert io.yaml_flow_map({"x": "y", "msg": "hello world"}) == '{ x: y, msg: "hello world" }'


def test_io_sha256_and_state(tmp_path):
    f = tmp_path / "sample.txt"
    io.write_text(f, "hello world\n")
    assert io.sha256_file(f) == io.sha256_bytes(b"hello world\n")

    proj = tmp_path / "my-project"
    proj.mkdir()
    state = io.load_state(proj)
    assert state == {}

    io.save_state(proj, round=1, seed=42)
    state2 = io.load_state(proj)
    assert state2["round"] == 1
    assert state2["seed"] == 42


def test_report_script_exit():
    with pytest.raises(report.ScriptExit) as exc:
        report.fail(report.EXIT_INVALID, "Gagal validasi", "run something")
    assert exc.value.code == report.EXIT_INVALID
    assert exc.value.lines == ["Gagal validasi"]
    assert exc.value.next_step == "run something"


def test_labels_and_placeholders():
    assert labels.fact_label("address", "id") == "alamat"
    assert labels.fact_label("address", "en") == "address"
    assert labels.placeholder("address", "id") == "[[ISI: alamat]]"
    assert labels.placeholder("address", "en") == "[[ISI: address]]"
    assert labels.placeholder("custom_unknown_fact", "id") == "[[ISI: custom unknown fact]]"


def test_project_open_and_brief_helpers(kopi):
    proj = project.open_project("kopi-senja", need=["brief.yaml"])
    assert proj.is_dir()

    brief = io.read_yaml(proj / "brief.yaml")
    assert not project.schema_errors(brief, "brief.schema.json")

    reqs = project.requirements(brief)
    req_ids = [r["id"] for r in reqs]
    assert "req-business.name" in req_ids
    assert "req-business.location" in req_ids
    assert "req-business.cultural_context" in req_ids
    assert "req-audience" in req_ids
    assert "req-facts.address" not in req_ids  # unknown, so not a requirement

    assert project.first_language(brief) == "id"
    assert project.is_unknown(brief, "facts.address")
    assert not project.is_unknown(brief, "business.location")

    st = project.load_site_type("company-profile")
    assert st["id"] == "company-profile"

    pages = project.site_pages(brief, st)
    assert "index" in pages
    assert "tentang" in pages
    assert "kontak" in pages

    styles = project.load_style_index()
    assert "neobrutalism" in styles
    assert "editorial" in styles

    neo = project.load_style("neobrutalism")
    assert neo["id"] == "neobrutalism"

    patterns = project.load_patterns()
    assert "hero" in patterns
    assert "split-offset" in patterns["hero"]
