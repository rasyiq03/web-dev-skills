# ============================================================
# File      : test_guided.py
# Deskripsi : Pengujian mode terpandu: aturan naik-turun tingkat dukungan,
#             profil developer, perintah checkpoint, dan satu build terpandu
#             dari brief sampai handoff.
# ============================================================

import pytest
from conftest import copy_fixture, next_line, run_script

from lib import explain, guided, io
from lib.report import EXIT_INVALID

PASSED = {"framing": "passed", "direction": "passed", "acceptance": "passed"}


def entry(level, **results):
    return {"project": f"p{level}{len(results)}", "level": level, "checkpoints": {**PASSED, **results}}


# ============================================================
# ====================== ATURAN TINGKAT ======================
# ============================================================


@pytest.mark.parametrize("level, history, expected", [
    (2, [], 2),
    (2, [entry(2)], 2),
    (2, [entry(2), entry(2)], 1),
    (2, [entry(3), entry(2)], 2),
    (2, [entry(2), entry(2, framing="skipped")], 2),
    (2, [entry(2), entry(2, acceptance="failed")], 3),
    (3, [entry(3, acceptance="failed")], 3),
    (0, [entry(0), entry(0)], 0),
    (1, [entry(2), entry(2), entry(1), entry(1)], 0),
])
def test_next_level_moves_at_most_one_step(level, history, expected):
    assert guided.next_level(level, history) == expected


def test_streak_resets_after_lowering(projects_dir):
    key = "proj"

    assert guided.record_project(f"{key}-1", 2, PASSED) == 2
    assert guided.record_project(f"{key}-2", 2, PASSED) == 1
    assert guided.record_project(f"{key}-3", 1, PASSED) == 1


def test_rerunning_handoff_does_not_count_twice(projects_dir):
    guided.record_project("same", 2, PASSED)
    guided.record_project("same", 2, PASSED)

    profile = guided.load_profile()

    assert len(profile["history"]) == 1
    assert profile["support_level"] == 2


def test_profile_defaults_and_brief_override(projects_dir):
    assert not guided.profile_path().exists()
    assert guided.load_profile() == {"support_level": 2, "history": []}
    assert guided.project_level({}) == 2
    assert guided.project_level({"support_level": 0}) == 0
    assert guided.profile_path() == projects_dir / "profile.yaml"


def test_results_and_next_checkpoint_from_trace():
    events = [
        {"event": "checkpoint", "checkpoint": "framing", "result": "failed"},
        {"event": "step", "script": "gaps"},
        {"event": "checkpoint", "checkpoint": "framing", "result": "passed"},
    ]
    results = guided.results_from_trace(events)

    assert results == {"framing": "passed"}
    assert guided.next_checkpoint(results) == "direction"
    assert guided.next_checkpoint({**PASSED}) is None


# ============================================================
# ======================== CHECKPOINT ========================
# ============================================================


@pytest.fixture
def guided_kopi(projects_dir):
    """
    Menyalin kopi-senja dan menyalakan mode terpandu di brief-nya.

    I.S. : projects_dir kosong.
    F.S. : brief.yaml dengan mode: guided dan directions.yaml ada; path proyek dikembalikan.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    brief = proj / "brief.yaml"
    brief.write_text(brief.read_text(encoding="utf-8").replace("interactive: false", "interactive: false\nmode: guided"), encoding="utf-8")

    return proj


def checkpoint(*args):
    return run_script("checkpoint", "kopi-senja", *args)


def test_checkpoint_refuses_auto_projects(kopi):
    result = run_script("checkpoint", "kopi-senja")

    assert result.returncode == EXIT_INVALID
    assert "tidak memakai mode terpandu" in result.stdout


def test_checkpoint_status_gives_level_instructions(guided_kopi):
    assert run_script("validate_brief", "kopi-senja").returncode == 0

    result = checkpoint()

    assert result.returncode == 0, result.stdout
    assert "Tingkat dukungan: 2 (Terbimbing), dari profil." in result.stdout
    assert "Next checkpoint: framing, after web-build step 1." in result.stdout
    assert guided.INSTRUCTIONS["framing"][2] in result.stdout
    assert next_line(result).startswith("NEXT: run the framing checkpoint")


def test_checkpoint_level_from_brief(guided_kopi):
    brief = guided_kopi / "brief.yaml"
    brief.write_text(brief.read_text(encoding="utf-8").replace("mode: guided", "mode: guided\nsupport_level: 3"), encoding="utf-8")
    assert run_script("validate_brief", "kopi-senja").returncode == 0

    result = checkpoint()

    assert "Tingkat dukungan: 3 (Demonstrasi), dari brief." in result.stdout
    assert guided.INSTRUCTIONS["framing"][3] in result.stdout


@pytest.mark.parametrize("args", [["framing"], ["framing", "--result", "passed", "--note", "ok"]])
def test_checkpoint_record_needs_result_and_note(guided_kopi, args):
    assert checkpoint(*args).returncode == EXIT_INVALID


def test_guided_build_end_to_end(guided_kopi):
    note = "Developer menyebut mahasiswa dan harga sebagai hal terpenting."

    assert run_script("validate_brief", "kopi-senja").returncode == 0
    assert checkpoint("framing", "--result", "passed", "--note", note).returncode == 0
    assert run_script("gaps", "kopi-senja").returncode == 0
    assert run_script("pick_direction", "kopi-senja", "--pick", "dir-2").returncode == 0
    assert run_script("decide", "kopi-senja", "d-style-1", "--accept", "--verification", "pick",
                      "--reason", "Cap tangan terasa milik pemilik kedai, cocok untuk mahasiswa.").returncode == 0
    assert checkpoint("direction", "--result", "passed", "--note", note).returncode == 0
    assert run_script("compile_tokens", "kopi-senja").returncode == 0
    assert run_script("scaffold", "kopi-senja").returncode == 0

    status = checkpoint()

    assert "Next checkpoint: acceptance" in status.stdout
    assert "Question 1 (explain back): why was layout:" in status.stdout
    assert "Question 2 (predict impact): if --pd-color-accent" in status.stdout
    assert "Reference chain:" in status.stdout
    assert "req-audience" in status.stdout

    assert checkpoint("acceptance", "--result", "passed", "--note", note).returncode == 0

    result = run_script("handoff", "kopi-senja")

    assert result.returncode == 0, result.stdout
    assert "Mode terpandu: tingkat 2 (Terbimbing); checkpoint: framing lolos, direction lolos, acceptance lolos" in result.stdout
    assert "Proyek berikutnya: tingkat 2 (Terbimbing)" in result.stdout

    profile = guided.load_profile()

    assert profile["history"][-1]["checkpoints"] == PASSED
    assert profile["history"][-1]["project"] == str(guided_kopi.resolve())

    page = (guided_kopi / "EXPLAIN.html").read_text(encoding="utf-8")

    assert ">Tingkat dukungan</h2>" in page
    assert "<tr><td>Menerima hasil</td><td>lolos</td></tr>" in page
    assert "Proyek berikutnya: Terbimbing (2)" in page


def test_second_passed_project_lowers_level(guided_kopi):
    guided.record_project("proyek-sebelumnya", 2, PASSED)

    for args in (("gaps",), ("pick_direction", "--pick", "dir-2"), ("compile_tokens",), ("scaffold",)):
        assert run_script(args[0], "kopi-senja", *args[1:]).returncode == 0

    for name in guided.CHECKPOINTS:
        assert checkpoint(name, "--result", "passed", "--note", "Jawaban developer sesuai rantai acuan.").returncode == 0

    result = run_script("handoff", "kopi-senja")

    assert "Proyek berikutnya: tingkat 1 (Petunjuk)" in result.stdout
    assert guided.load_profile()["support_level"] == 1


def test_missing_checkpoints_count_as_skipped(guided_kopi):
    for args in (("gaps",), ("pick_direction", "--pick", "dir-2"), ("compile_tokens",), ("scaffold",)):
        assert run_script(args[0], "kopi-senja", *args[1:]).returncode == 0

    result = run_script("handoff", "kopi-senja")

    assert "framing dilewati, direction dilewati, acceptance dilewati" in result.stdout
    assert guided.load_profile()["support_level"] == 2


def test_auto_mode_never_touches_the_profile(kopi):
    copy_fixture(kopi.parent.parent, "kopi-senja", ["directions.yaml"])

    for args in (("gaps",), ("pick_direction", "--pick", "dir-2"), ("compile_tokens",), ("scaffold",), ("handoff",)):
        assert run_script(args[0], "kopi-senja", *args[1:]).returncode == 0

    assert not guided.profile_path().exists()
    assert "Tingkat dukungan" not in explain.build_html(kopi)
