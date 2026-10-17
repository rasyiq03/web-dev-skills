# ============================================================
# File      : test_signals.py
# Deskripsi : Pengujian sinyal Agentivism P1-P6 di HANDOFF.md dan
#             EXPLAIN.html, serta alat tools/eval/collect.py yang
#             menulis satu CSV untuk membandingkan mode.
# ============================================================

import csv

import pytest
from conftest import copy_fixture, run_script, run_tool

from lib import explain, signals


def build(projects_dir, mode=None, pick=True):
    """
    Membangun kopi-senja sampai handoff, dengan mode dan cara memilih arah tertentu.

    I.S. : projects_dir kosong.
    F.S. : Proyek sudah handoff; path folder proyek dikembalikan.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])

    if mode:
        brief = proj / "brief.yaml"
        brief.write_text(brief.read_text(encoding="utf-8").replace("interactive: false", f"interactive: false\nmode: {mode}"), encoding="utf-8")

    choose = ("pick_direction", "--pick", "dir-2") if pick else ("pick_direction", "--seed", "7")

    for args in (("gaps",), choose, ("compile_tokens",), ("scaffold",)):
        assert run_script(args[0], "kopi-senja", *args[1:]).returncode == 0

    return proj


def handoff_signals(proj):
    assert run_script("handoff", "kopi-senja").returncode == 0
    text = (proj / "HANDOFF.md").read_text(encoding="utf-8")

    return text[text.index("## 7. Sinyal pembelajaran (Agentivism)"):]


def test_client_pick_counts_as_responsibility_and_verification(projects_dir):
    proj = build(projects_dir)
    found = signals.compute(proj)

    assert (found["p1_owned"], found["decisions"], found["p2_verifications"], found["p6_risk"]) == (6, 6, 1, "low")

    section = handoff_signals(proj)

    assert "P1 Tanggung jawab tetap pada Anda: 6 dari 6 keputusan" in section
    assert "P6 Risiko ketergantungan: rendah" in section
    assert "tidak ditanyakan (bukan mode terpandu)" in section


def test_sampled_direction_without_checks_is_high_risk(projects_dir):
    proj = build(projects_dir, pick=False)

    section = handoff_signals(proj)

    assert "P1 Tanggung jawab tetap pada Anda: 0 dari 6 keputusan" in section
    assert "P6 Risiko ketergantungan: tinggi. Tidak ada keputusan yang Anda periksa sendiri." in section


def test_developer_changes_count_as_rework(projects_dir):
    proj = build(projects_dir, pick=False)
    assert run_script("decide", "kopi-senja", "d-motion-1", "--choice", "none",
                      "--reason", "Hemat kuota data pengunjung.").returncode == 0

    found = signals.compute(proj)

    assert (found["p1_owned"], found["p2_verifications"], found["p3_changed"], found["p6_risk"]) == (1, 1, 1, "low")


def test_ai_changes_do_not_count_for_the_developer(projects_dir):
    proj = build(projects_dir, pick=False)
    assert run_script("decide", "kopi-senja", "d-motion-1", "--choice", "none", "--by", "ai",
                      "--reason", "Perbaikan check oleh AI.").returncode == 0

    found = signals.compute(proj)

    assert (found["p2_verifications"], found["p3_changed"], found["p6_risk"]) == (0, 0, "high")


def test_guided_acceptance_appears_next_to_check_scores(projects_dir):
    proj = build(projects_dir, mode="guided")
    assert run_script("checkpoint", "kopi-senja", "acceptance", "--result", "passed",
                      "--note", "Jawaban sesuai rantai acuan.").returncode == 0

    assert "uji pemahaman: lolos" in handoff_signals(proj)


def test_deep_mode_risk_explains_itself(projects_dir):
    proj = build(projects_dir, mode="deep", pick=False)

    section = handoff_signals(proj)

    assert "wajar di mode deep work" in section
    assert ">Sinyal pembelajaran (Agentivism)</h2>" in explain.build_html(proj)


def test_collect_writes_one_csv_row_per_project(projects_dir):
    build(projects_dir)
    out = projects_dir / "hasil" / "eval.csv"

    result = run_tool("eval/collect", str(projects_dir), "--out", str(out))

    assert result.returncode == 0, result.stdout
    assert "auto: 1 proyek, P1 rata-rata 1.00" in result.stdout

    rows = list(csv.DictReader(out.open(encoding="utf-8")))

    assert len(rows) == 1
    assert rows[0]["project"].endswith("/kopi-senja")
    assert rows[0]["mode"] == "auto"
    assert rows[0]["p1_share"] == "1.0"
    assert rows[0]["ready"] == "False"

    first = out.read_bytes()
    run_tool("eval/collect", str(projects_dir), "--out", str(out))

    assert out.read_bytes() == first


def test_collect_without_projects_exits_1(projects_dir):
    result = run_tool("eval/collect", str(projects_dir), "--out", str(projects_dir / "x.csv"))

    assert result.returncode == 1
    assert "Tidak ada proyek" in result.stdout
