# ============================================================
# File      : test_graph.py
# Deskripsi : Pengujian graf konteks: isi graph.json untuk kopi-senja,
#             pertanyaan --impact dan --why, determinisme, dan pembaruan
#             otomatis oleh skrip pipeline.
# ============================================================

import json

import pytest
from conftest import copy_fixture, next_line, run_script

from lib import graph


@pytest.fixture
def kopi_tokens(projects_dir):
    """
    Menyiapkan kopi-senja sampai token tersusun (belum scaffold).

    I.S. : projects_dir kosong.
    F.S. : gaps, decisions, dan tokens kopi-senja ada; path folder proyek dikembalikan.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])

    for args in (("gaps",), ("pick_direction", "--pick", "dir-2"), ("compile_tokens",)):
        result = run_script(args[0], "kopi-senja", *args[1:])
        assert result.returncode == 0, result.stdout

    return proj


def load(proj):
    return json.loads((proj / "graph.json").read_text(encoding="utf-8"))


def edge_set(context_graph):
    return {(e["from"], e["to"], e["type"]) for e in context_graph["edges"]}


def test_pipeline_scripts_keep_graph_current(kopi_tokens):
    context_graph = load(kopi_tokens)
    nodes = graph.index(context_graph)

    assert context_graph["project"] == "kopi-senja"
    assert nodes["req-audience"]["owner"] == "developer"
    assert nodes["req-business.cultural_context"]["owner"] == "ai"
    assert nodes["d-palette-1"]["owner"] == "developer"
    assert nodes["d-palette-1"]["why"].startswith("Kraft paper")
    assert nodes["token:color.accent"]["label"] == "--pd-color-accent"
    assert nodes["section:index#hero"]["pattern"] == "split-offset"


def test_graph_links_requirement_to_check(kopi_tokens):
    edges = edge_set(load(kopi_tokens))

    assert ("d-palette-1", "req-audience", "based_on") in edges
    assert ("d-palette-1", "token:color.accent", "realized_by") in edges
    assert ("d-palette-1", "check:c-contrast-accent", "verified_by") in edges
    assert ("check:c-contrast-accent", "token:color.accent", "about") in edges
    assert ("d-layout-1", "section:index#hero", "realized_by") in edges
    assert ("ph:services", "section:index#services", "fills") in edges
    assert ("page:index", "section:index#hero", "contains") in edges


def test_scaffold_adds_files(kopi_tokens):
    assert "file:css/tokens.css" not in graph.index(load(kopi_tokens))

    result = run_script("scaffold", "kopi-senja")
    assert result.returncode == 0, result.stdout

    edges = edge_set(load(kopi_tokens))

    assert ("token:color.accent", "file:css/tokens.css", "located_in") in edges
    assert ("section:index#hero", "file:index.html", "located_in") in edges
    assert ("section:tentang#story", "file:pages/tentang.html", "located_in") in edges


def test_constraint_findings_violate_their_check(kopi_tokens):
    report_data = {
        "findings": [
            {"rule": "constraint-c-contrast-body", "level": "error", "message": "kontras 3.1"},
            {"rule": "no-unused-vars", "level": "warning", "file": "js/main.js", "line": 4},
        ],
    }
    (kopi_tokens / "report.json").write_text(json.dumps(report_data), encoding="utf-8")

    context_graph = graph.refresh(kopi_tokens)
    edges = edge_set(context_graph)

    assert ("finding:1", "check:c-contrast-body", "violates") in edges
    assert ("finding:2", "file:js/main.js", "located_in") in edges

    why_ids = [node_id for node_id, *_ in graph.why(context_graph, "finding:1")]
    assert why_ids[:2] == ["check:c-contrast-body", "d-palette-1"]


def test_graph_is_deterministic(kopi_tokens):
    first = (kopi_tokens / "graph.json").read_bytes()
    graph.refresh(kopi_tokens)

    assert (kopi_tokens / "graph.json").read_bytes() == first


def test_impact_of_decision_reaches_tokens_and_checks(kopi_tokens):
    found = {node_id for node_id, *_ in graph.impact(load(kopi_tokens), "d-palette-1")}

    assert {"token:color.accent", "token:color.paper", "check:c-contrast-body"} <= found
    assert "req-audience" not in found
    assert "d-typo-1" not in found


def test_impact_of_requirement_reaches_every_decision_citing_it(kopi_tokens):
    found = {node_id for node_id, *_ in graph.impact(load(kopi_tokens), "req-audience")}

    assert {"d-style-1", "d-palette-1", "d-typo-1", "d-layout-1", "d-motion-1", "d-tone-1"} <= found


def test_why_of_token_walks_back_to_requirements(kopi_tokens):
    visits = graph.why(load(kopi_tokens), "token:color.accent")

    assert [v[0] for v in visits] == ["d-palette-1", "req-audience", "req-business.location"]
    assert visits[0][3] is False
    assert visits[1][3] is True


def test_resolve_accepts_name_without_prefix(kopi_tokens):
    context_graph = load(kopi_tokens)

    assert graph.resolve(context_graph, "color.accent") == "token:color.accent"
    assert graph.resolve(context_graph, "d-palette-1") == "d-palette-1"
    assert graph.resolve(context_graph, "tidak-ada") is None


def test_cli_why_reads_in_the_right_direction(kopi_tokens):
    result = run_script("graph", "kopi-senja", "--why", "color.accent")

    assert result.returncode == 0, result.stdout
    assert "token:color.accent mewujudkan -> d-palette-1" in result.stdout
    assert "d-palette-1 berdasar pada -> req-audience" in result.stdout
    assert next_line(result) == "NEXT: tell the user why, in plain words"


def test_cli_impact_uses_inverse_words(kopi_tokens):
    result = run_script("graph", "kopi-senja", "--impact", "req-audience")

    assert result.returncode == 0, result.stdout
    assert "req-audience menjadi dasar untuk -> d-palette-1" in result.stdout


def test_cli_summary_and_unknown_node(kopi_tokens):
    result = run_script("graph", "kopi-senja")

    assert result.returncode == 0
    assert "Graf konteks:" in result.stdout

    missing = run_script("graph", "kopi-senja", "--why", "tidak-ada")

    assert missing.returncode == 1
    assert "tidak ditemukan" in missing.stdout


def test_graph_works_with_brief_only(kopi):
    result = run_script("graph", "kopi-senja")

    assert result.returncode == 0, result.stdout
    assert "page:index" in graph.index(load(kopi))


def test_placeholders_written_on_pages_join_the_graph(kopi_tokens):
    assert run_script("scaffold", "kopi-senja").returncode == 0
    index = kopi_tokens.parent / "index.html"
    index.write_text(index.read_text(encoding="utf-8").replace(
        "</main>", "<p>[[ISI: cara pembayaran]] [[ISI: jam buka]]</p></main>"), encoding="utf-8")

    context_graph = graph.refresh(kopi_tokens)
    nodes = {node["id"]: node for node in context_graph["nodes"]}

    # Placeholder baru dari halaman terdaftar; yang sudah ada dari gaps tidak digandakan
    assert nodes["ph:site:cara-pembayaran"]["label"] == "[[ISI: cara pembayaran]]"
    assert ("ph:site:cara-pembayaran", "file:index.html", "located_in") in edge_set(context_graph)
    assert not any(node_id.startswith("ph:site:jam") for node_id in nodes)
