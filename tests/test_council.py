# ============================================================
# File      : test_council.py
# Deskripsi : Pengujian mode deep work: aturan musyawarah pada notulen,
#             voting berbobot, perintah council (paket dan --record), dan
#             satu build deep work dari brief sampai handoff.
# ============================================================

import copy

import pytest
from conftest import copy_fixture, next_line, run_script

from lib import council, explain, graph, io, trace
from lib.report import EXIT_INVALID


def minutes_for(sitting, outcome="dir-2", simulated=False):
    """
    Menyusun notulen sah untuk satu sidang: semua anggota bicara, kritik saling memperbaiki.

    I.S. : -
    F.S. : dict notulen yang lolos validate_minutes() dikembalikan.
    """
    members = list(council.MEMBERS)
    proposals = [
        {"role": role, "text": f"Saya usul {outcome} karena cocok untuk mahasiswa.", "choice": outcome,
         "evidence": ["req-audience"]}
        for role in members
    ]
    critique = [
        {"role": role, "target_role": members[(i + 1) % len(members)],
         "text": "Usulan itu lebih kuat bila menyebut lokasi Bandung juga."}
        for i, role in enumerate(members)
    ]

    return {
        "sitting": sitting,
        "simulated": simulated,
        "roles": members,
        "rounds": [
            {"round": 1, "kind": "proposals", "entries": proposals},
            {"round": 2, "kind": "critique", "entries": critique},
        ],
        "resolution": {"method": "mufakat", "outcome": outcome, "summary": "Semua anggota sepakat tanpa keberatan."},
    }


DIRECTIONS = {"directions": [{"id": f"dir-{n}"} for n in range(1, 6)]}


@pytest.fixture
def kopi_graph(projects_dir):
    """
    Menyiapkan graf kopi-senja sampai gaps, untuk memeriksa bukti notulen.

    I.S. : projects_dir kosong.
    F.S. : (folder proyek, graf) dikembalikan.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    assert run_script("gaps", "kopi-senja").returncode == 0

    return proj, graph.build(proj)


# ============================================================
# ========================== SUARA ===========================
# ============================================================


@pytest.mark.parametrize("votes, expected", [
    ({"perancang": "dir-1", "penulis": "dir-2", "arsitek": "dir-2", "penguji": "dir-1", "wakil-klien": "dir-3"}, "dir-1"),
    ({"perancang": "dir-1", "penulis": "dir-2", "arsitek": "dir-2", "penguji": "dir-2", "wakil-klien": "dir-3"}, "dir-2"),
    ({"perancang": "dir-4", "penulis": "dir-2", "arsitek": "dir-2", "penguji": "dir-3", "wakil-klien": "dir-5"}, "dir-4"),
])
def test_weighted_vote_counts_topic_owner_twice(votes, expected):
    ballots = [{"role": role, "choice": choice} for role, choice in votes.items()]

    assert council.weighted_outcome("direction", ballots) == expected


# ============================================================
# ========================= NOTULEN ==========================
# ============================================================


def test_valid_minutes_pass(kopi_graph):
    assert council.validate_minutes(minutes_for("direction"), kopi_graph[1], DIRECTIONS) == []


def broken(change):
    data = minutes_for("direction")
    change(data)

    return data


CASES = {
    "member silent in round 1": (lambda m: m["rounds"][0]["entries"].pop(), "setiap anggota bicara tepat sekali"),
    "critique of own proposal": (lambda m: m["rounds"][1]["entries"][0].update(target_role="perancang"), "memperbaiki usulan anggota lain"),
    "block without evidence": (lambda m: m["rounds"][1]["entries"][0].update(objection="Kontras terlalu lemah di layar HP.", blocking=True), "memblokir tanpa bukti"),
    "evidence not in graph": (lambda m: m["rounds"][0]["entries"][0].update(evidence=["req-tidak-ada"]), "tidak ada di graf"),
    "mufakat with open block": (lambda m: m["rounds"][1]["entries"][0].update(objection="Kontras terlalu lemah di layar HP.", blocking=True, evidence=["req-audience"]), "Mufakat belum tercapai"),
    "outcome not a direction": (lambda m: m["resolution"].update(outcome="dir-9"), "harus salah satu dari"),
    "member absent": (lambda m: m["roles"].remove("penguji"), "Semua anggota harus hadir"),
    "too many rounds": (lambda m: m["rounds"].extend(copy.deepcopy(m["rounds"])), "Skema notulen"),
    "bad veto placeholder": (lambda m: m["resolution"].update(vetoes=[{"fact": "harga", "placeholder": "Rp18.000"}]), "Skema notulen"),
}


@pytest.mark.parametrize("name", CASES)
def test_rule_breaks_are_reported(kopi_graph, name):
    change, message = CASES[name]
    errors = council.validate_minutes(broken(change), kopi_graph[1], DIRECTIONS)

    assert any(message in err for err in errors), errors


def test_resolved_block_allows_mufakat(kopi_graph):
    data = minutes_for("direction")
    data["rounds"][1]["entries"][0].update(objection="Kontras terlalu lemah di layar HP.", blocking=True,
                                           evidence=["req-audience"], resolved=True)

    assert council.validate_minutes(data, kopi_graph[1], DIRECTIONS) == []


def test_vote_must_match_weighted_count(kopi_graph):
    data = minutes_for("direction")
    data["rounds"][1]["entries"][0].update(objection="Kontras terlalu lemah di layar HP.", blocking=True, evidence=["req-audience"])
    votes = {"perancang": "dir-1", "penulis": "dir-2", "arsitek": "dir-2", "penguji": "dir-1", "wakil-klien": "dir-3"}
    data["resolution"].update(method="vote", outcome="dir-2", votes=[{"role": r, "choice": c} for r, c in votes.items()])

    assert any("Hasil voting berbobot adalah 'dir-1'" in e for e in council.validate_minutes(data, kopi_graph[1], DIRECTIONS))

    data["resolution"]["outcome"] = "dir-1"

    assert council.validate_minutes(data, kopi_graph[1], DIRECTIONS) == []


# ============================================================
# ========================== PERINTAH ========================
# ============================================================


@pytest.fixture
def deep_kopi(projects_dir):
    """
    Menyalin kopi-senja dengan mode deep work dan menjalankan validate_brief serta gaps.

    I.S. : projects_dir kosong.
    F.S. : Proyek mode deep dengan directions.yaml; path folder proyek dikembalikan.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    brief = proj / "brief.yaml"
    brief.write_text(brief.read_text(encoding="utf-8").replace("interactive: false", "interactive: false\nmode: deep"), encoding="utf-8")

    for name in ("validate_brief", "gaps"):
        assert run_script(name, "kopi-senja").returncode == 0

    return proj


def sit(proj, sitting, **kwargs):
    io.write_yaml(proj / "deliberation" / f"{sitting}.yaml", minutes_for(sitting, **kwargs))

    return run_script("council", "kopi-senja", sitting, "--record")


def test_council_refuses_auto_projects(kopi):
    assert run_script("gaps", "kopi-senja").returncode == 0

    result = run_script("council", "kopi-senja", "direction")

    assert result.returncode == EXIT_INVALID
    assert "tidak memakai mode deep work" in result.stdout


def test_packet_holds_rules_evidence_and_directions(deep_kopi):
    result = run_script("council", "kopi-senja", "direction")

    assert result.returncode == 0, result.stdout
    assert "references/council/wakil-klien.md" in result.stdout
    assert "Pemilik topik (suara ganda saat voting): Perancang" in result.stdout

    packet = (deep_kopi / "deliberation" / "direction.packet.md").read_text(encoding="utf-8")

    assert "# Sidang arah desain" in packet
    assert "musyawarah untuk mufakat" in packet
    assert "`req-audience`" in packet
    assert "### dir-2 (24%)" in packet


def test_record_direction_picks_with_council_source(deep_kopi):
    result = sit(deep_kopi, "direction", outcome="dir-3")

    assert result.returncode == 0, result.stdout
    assert next_line(result) == "NEXT: run compile_tokens.py"
    assert "mufakat, hasil dir-3" in result.stdout

    decisions = io.read_yaml(deep_kopi / "decisions.yaml")
    context_graph = graph.build(deep_kopi)
    edges = {(e["from"], e["to"], e["type"]) for e in context_graph["edges"]}

    assert decisions["direction"] == "dir-3"
    assert {d["source"] for d in decisions["decisions"]} == {"council"}
    assert graph.index(context_graph)["d-palette-1"]["owner"] == "council"
    assert ("d-palette-1", "minutes:direction", "decided_in") in edges
    assert "minutes:direction" in [v[0] for v in graph.why(context_graph, "d-palette-1")]
    assert trace.read(deep_kopi)[-1]["event"] == "council"


def test_invalid_minutes_change_nothing(deep_kopi):
    data = minutes_for("direction")
    data["rounds"][0]["entries"].pop()
    io.write_yaml(deep_kopi / "deliberation" / "direction.yaml", data)

    result = run_script("council", "kopi-senja", "direction", "--record")

    assert result.returncode == EXIT_INVALID
    assert "Notulen belum sesuai aturan musyawarah" in result.stdout
    assert not (deep_kopi / "decisions.yaml").exists()
    assert not [e for e in trace.read(deep_kopi) if e["event"] == "council"]


def test_simulated_council_is_labelled(deep_kopi):
    result = sit(deep_kopi, "direction", simulated=True)

    assert result.returncode == 0, result.stdout
    assert "dewan disimulasikan oleh satu agen" in result.stdout
    assert graph.index(graph.build(deep_kopi))["minutes:direction"]["simulated"] is True


# ============================================================
# ========================= GERBANG ==========================
# ============================================================

CONTENT = """pages:
  index:
    title: Kopi Senja — kedai kopi di Bandung
    description: Kedai kopi santai di Bandung untuk mahasiswa dan penikmat kopi.
    sections:
      hero: { heading: Kopi Senja, body: Kopi hangat di Bandung untuk kamu yang suka membaca. }
      services: { heading: Menu, items: [{ name: Kopi susu, price: "[[ISI: daftar layanan atau menu]]" }] }
      proof: { heading: Rekam jejak, body: "[[ISI: tahun berdiri]]" }
  tentang:
    title: Tentang Kopi Senja
    description: Cerita Kopi Senja di Bandung.
    sections:
      story: { heading: Awal mula, body: "[[ISI: nama dan peran tim]]" }
  kontak:
    title: Kontak Kopi Senja
    description: Cara menghubungi Kopi Senja di Bandung.
    sections:
      contact: { heading: Hubungi kami, body: "[[ISI: alamat]]" }
"""


@pytest.mark.node
def test_deep_work_build_end_to_end(deep_kopi):
    assert sit(deep_kopi, "direction").returncode == 0

    for name in ("compile_tokens", "scaffold"):
        assert run_script(name, "kopi-senja").returncode == 0

    assert sit(deep_kopi, "copy", outcome="copy-agreed", simulated=True).returncode == 0
    io.write_text(deep_kopi / "content" / "id.yaml", CONTENT)
    assert sit(deep_kopi, "first-page", outcome="fixes-agreed").returncode == 0
    assert sit(deep_kopi, "site", outcome="fixes-agreed").returncode == 0

    checked = run_script("check", "kopi-senja")
    summary = io.read_json(deep_kopi / "report.json")["summary"]

    assert checked.returncode == 0, checked.stdout
    assert summary["errors"] == 0

    result = run_script("handoff", "kopi-senja")

    assert result.returncode == 0, result.stdout
    assert "Mode deep work: sidang tercatat direction (mufakat), copy (mufakat), first-page (mufakat), site (mufakat)" in result.stdout
    assert "Sebagian sidang disimulasikan oleh satu agen" in result.stdout

    if summary["warnings"] == 0:
        assert "Siap pakai" in result.stdout
    else:
        assert f"Belum siap pakai: check: 0 error, {summary['warnings']} peringatan" in result.stdout

    minutes = [n for n in graph.build(deep_kopi)["nodes"] if n["type"] == "minutes"]
    page = explain.build_html(deep_kopi)

    assert [n["label"] for n in minutes] == list(council.SITTINGS)
    assert ">Musyawarah dewan AI</h2>" in page
    assert 'href="deliberation/direction.yaml"' in page
    assert "voting berbobot" not in page
    assert "disimulasikan satu agen" in page


def test_handoff_says_what_is_missing(deep_kopi):
    assert sit(deep_kopi, "direction").returncode == 0

    for name in ("compile_tokens", "scaffold"):
        assert run_script(name, "kopi-senja").returncode == 0

    result = run_script("handoff", "kopi-senja")

    assert "Belum siap pakai: sidang belum diadakan: copy, first-page, site; check belum dijalankan" in result.stdout
