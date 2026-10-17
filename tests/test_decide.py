# ============================================================
# File      : test_decide.py
# Deskripsi : Pengujian decide.py dan trace.jsonl: perubahan satu keputusan
#             hanya menyentuh bagian hilirnya di graf, penerimaan dicatat,
#             masukan salah tidak mengubah apa pun, dan gagal di tengah jalan
#             mengembalikan decisions.yaml.
# ============================================================

import argparse

import pytest
from conftest import copy_fixture, next_line, run_script

from lib import graph, io, trace
from lib.report import EXIT_INVALID, ScriptExit


@pytest.fixture
def kopi_site(projects_dir):
    """
    Menyiapkan kopi-senja sampai scaffold.

    I.S. : projects_dir kosong.
    F.S. : Proyek kopi-senja dengan site/ ada; path folder proyek dikembalikan.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])

    for args in (("gaps",), ("pick_direction", "--pick", "dir-2"), ("compile_tokens",), ("scaffold",)):
        result = run_script(args[0], "kopi-senja", *args[1:])
        assert result.returncode == 0, result.stdout

    return proj


def decide(*args):
    return run_script("decide", "kopi-senja", *args)


def changed_nodes(before, after):
    old, new = graph.index(before), graph.index(after)

    return {node_id for node_id in old.keys() | new.keys() if old.get(node_id) != new.get(node_id)}


CHANGES = [
    ("d-palette-1", ["--choice", "sun-block"], "token:color.accent"),
    ("d-typo-1", ["--choice", "wide-display"], "token:font.display"),
    ("d-motion-1", ["--choice", "none"], "d-motion-1"),
    ("d-layout-1", ["--section", "hero", "--choice", "full-bleed-type"], "section:index#hero"),
    ("d-tone-1", ["--choice", "resmi-hangat", "--register", "id=Anda"], "d-tone-1"),
]


@pytest.mark.parametrize("decision, extra, must_change", CHANGES)
def test_change_touches_only_downstream_nodes(kopi_site, decision, extra, must_change):
    before = graph.build(kopi_site)
    downstream = {node_id for node_id, *_ in graph.impact(before, decision)} | {decision}

    result = decide(decision, *extra, "--reason", "Alasan uji yang menyebut mahasiswa.")
    assert result.returncode == 0, result.stdout

    changed = changed_nodes(before, graph.build(kopi_site))

    assert must_change in changed
    assert changed <= downstream, f"berubah di luar hilir: {sorted(changed - downstream)}"


def test_palette_change_rebuilds_tokens_and_site_css(kopi_site):
    result = decide("d-palette-1", "--choice", "sun-block", "--reason", "Warna cerah untuk layar HP di siang hari.")

    assert result.returncode == 0, result.stdout
    assert next_line(result) == "NEXT: run check"
    assert "warm-paper -> sun-block" in result.stdout

    decisions = io.read_yaml(kopi_site / "decisions.yaml")
    palette = next(d for d in decisions["decisions"] if d["id"] == "d-palette-1")
    others = [d["source"] for d in decisions["decisions"] if d["id"] != "d-palette-1"]

    assert palette["source"] == "overridden"
    assert palette["rationale"] == "Warna cerah untuk layar HP di siang hari."
    assert set(others) == {"client-picked"}
    assert decisions["overrides"]["palette"] == "sun-block"
    assert (kopi_site / "site" / "css" / "tokens.css").read_bytes() == (kopi_site / "tokens.css").read_bytes()


def test_typography_change_swaps_font_link_in_every_page(kopi_site):
    result = decide("d-typo-1", "--choice", "wide-display", "--reason", "Judul lebar terbaca dari jauh.")

    assert result.returncode == 0, result.stdout

    for page in ("index.html", "pages/tentang.html", "pages/kontak.html"):
        text = (kopi_site / "site" / page).read_text(encoding="utf-8")
        assert "family=Unbounded" in text, page
        assert "family=Archivo+Black" not in text, page


def test_layout_change_retags_only_that_section(kopi_site):
    result = decide("d-layout-1", "--section", "hero", "--choice", "full-bleed-type", "--reason", "Nama kedai harus tampil besar.")

    assert result.returncode == 0, result.stdout
    assert next_line(result) == "NEXT: rebuild the listed section with its new pattern, then run check"

    index_html = (kopi_site / "site" / "index.html").read_text(encoding="utf-8")

    assert 'data-pd-pattern="full-bleed-type"' in index_html
    assert 'data-pd-pattern="list-with-prices"' in index_html


def test_overrides_accumulate_and_survive_compile_tokens(kopi_site):
    assert decide("d-palette-1", "--choice", "sun-block", "--reason", "Warna cerah untuk siang hari.").returncode == 0
    assert decide("d-motion-1", "--choice", "none", "--reason", "Hemat kuota data pengunjung.").returncode == 0
    assert run_script("compile_tokens", "kopi-senja").returncode == 0

    overrides = io.read_yaml(kopi_site / "decisions.yaml")["overrides"]

    assert overrides["palette"] == "sun-block"
    assert overrides["motion"] == "none"
    assert set(overrides["rationale"]) == {"color", "motion"}
    assert "#D7263D" in (kopi_site / "tokens.css").read_text(encoding="utf-8")


def test_accept_records_verification_without_changing_decision(kopi_site):
    before = (kopi_site / "decisions.yaml").read_bytes()

    result = decide("d-palette-1", "--accept", "--verification", "compare", "--reason", "Lebih cocok dari ink-on-cream.")

    assert result.returncode == 0, result.stdout
    assert (kopi_site / "decisions.yaml").read_bytes() == before

    event = trace.read(kopi_site)[-1]
    node = graph.index(graph.build(kopi_site))["d-palette-1"]

    assert event["event"] == "accept"
    assert event["verification"] == "compare"
    assert node["accepted_by"] == "developer"
    assert node["verification"] == "compare"
    assert node["owner"] == "developer"


def test_change_by_ai_makes_ai_the_owner(kopi_site):
    assert decide("d-motion-1", "--choice", "none", "--by", "ai", "--reason", "Hemat kuota data pengunjung.").returncode == 0

    assert graph.index(graph.build(kopi_site))["d-motion-1"]["owner"] == "ai"


@pytest.mark.parametrize("args", [
    ["d-style-1", "--choice", "editorial"],
    ["d-palette-1", "--choice", "tidak-ada"],
    ["d-layout-1", "--choice", "full-bleed-type"],
    ["d-tidak-ada", "--choice", "x"],
    ["d-palette-1"],
    ["d-palette-1", "--choice", "sun-block", "--reason", "pendek"],
])
def test_invalid_requests_change_nothing(kopi_site, args):
    decisions_before = (kopi_site / "decisions.yaml").read_bytes()
    trace_before = len(trace.read(kopi_site))

    if "--reason" not in args:
        args = [*args, "--reason", "Alasan uji yang cukup panjang."]

    result = decide(*args)

    assert result.returncode == EXIT_INVALID, result.stdout
    assert (kopi_site / "decisions.yaml").read_bytes() == decisions_before
    assert len(trace.read(kopi_site)) == trace_before


def test_failed_downstream_restores_decisions(kopi_site, monkeypatch):
    import decide as decide_script

    def broken(slug):
        raise ScriptExit(EXIT_INVALID, ["kontras gagal"], "fix it")

    monkeypatch.setattr(decide_script.tokens_script, "compile_tokens", broken)
    before = (kopi_site / "decisions.yaml").read_bytes()
    decisions = io.read_yaml(kopi_site / "decisions.yaml")
    decision = next(d for d in decisions["decisions"] if d["id"] == "d-palette-1")
    args = argparse.Namespace(choice="sun-block", section=None, register=None, reason="Alasan uji yang cukup panjang.", by="developer", verification="justify")

    with pytest.raises(ScriptExit):
        decide_script.change("kopi-senja", kopi_site, decisions, decision, args)

    assert (kopi_site / "decisions.yaml").read_bytes() == before
    assert not [e for e in trace.read(kopi_site) if e["event"] == "decide"]


def test_pipeline_scripts_record_steps(kopi_site):
    steps = [e["script"] for e in trace.read(kopi_site) if e["event"] == "step"]

    assert steps == ["gaps", "pick_direction", "compile_tokens", "scaffold"]
    assert [e["seq"] for e in trace.read(kopi_site)] == [1, 2, 3, 4]
    assert {e["date"] for e in trace.read(kopi_site)} == {"2026-10-08"}


def test_explain_marks_the_current_choice_after_a_change(kopi_site):
    from lib import explain

    assert decide("d-palette-1", "--choice", "mint-signal", "--reason", "Hijau segar untuk kedai pagi hari.").returncode == 0

    page = explain.build_html(kopi_site)

    assert "mint-signal · tidak ada di kelima arah · dipilih" in page
    assert "warm-paper · 24%</li>" in page
    assert "diubah setelah arah dipilih" in page


def test_explain_shows_who_accepted_and_how(kopi_site):
    from lib import explain

    assert decide("d-typo-1", "--accept", "--verification", "predict", "--reason", "Saya menebak pasangan ini sebelum melihat.").returncode == 0

    assert "Diterima oleh</dt><dd>Anda · menebak dulu sebelum melihat" in explain.build_html(kopi_site)
