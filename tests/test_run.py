# ============================================================
# File      : test_run.py
# Deskripsi : Pengujian run.py: penolakan perintah tak dikenal, penerusan
#             ke skrip, kode keluar skrip, dan subperintah path.
# ============================================================

from pathlib import Path

from conftest import REPO, next_line, run_script


def printed_project(result):
    """
    Mengambil folder dari baris PROJECT: keluaran run.py path.

    I.S. : result adalah CompletedProcess run.py path.
    F.S. : Path dikembalikan, atau None bila tidak ada baris PROJECT:.
    """
    lines = [line for line in result.stdout.splitlines() if line.startswith("PROJECT: ")]

    return Path(lines[-1].removeprefix("PROJECT: ")) if lines else None


def test_run_unknown_command_lists_valid_names():
    result = run_script("run", "deploy", "kopi-senja")

    assert result.returncode == 1
    assert "validate_brief" in result.stdout
    assert "path" in result.stdout
    assert next_line(result) == "NEXT: use one of the listed commands"


def test_run_without_command_fails():
    result = run_script("run")

    assert result.returncode == 1


def test_run_dispatches_to_script(kopi):
    direct = run_script("validate_brief", "kopi-senja")
    via_run = run_script("run", "validate_brief", "kopi-senja")

    assert direct.returncode == 0
    assert via_run.returncode == 0
    assert next_line(via_run) == next_line(direct) == "NEXT: run gaps.py"


def test_run_passes_script_exit_code_through(projects_dir):
    result = run_script("run", "validate_brief", "belum-ada")

    assert result.returncode == 1
    assert next_line(result).startswith("NEXT: write ")


def test_run_path_outside_repo(monkeypatch, tmp_path):
    monkeypatch.delenv("PD_PROJECTS_DIR", raising=False)

    result = run_script("run", "path", "kopi-senja", cwd=tmp_path)

    assert result.returncode == 0, result.stdout
    assert printed_project(result) == tmp_path.resolve() / "kopi-senja"
    assert next_line(result) == "NEXT: write the project files in that folder"
    assert not (tmp_path / "kopi-senja").exists()


def test_run_path_in_repo(monkeypatch):
    monkeypatch.delenv("PD_PROJECTS_DIR", raising=False)

    result = run_script("run", "path", "kopi-senja", cwd=REPO)

    assert printed_project(result) == REPO / "projects" / "kopi-senja"


def test_run_path_env_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("PD_PROJECTS_DIR", str(tmp_path))

    result = run_script("run", "path", "kopi-senja", cwd=REPO)

    assert printed_project(result) == tmp_path.resolve() / "kopi-senja"


def test_run_path_rejects_invalid_slug():
    result = run_script("run", "path", "Kopi Senja")

    assert result.returncode == 1
