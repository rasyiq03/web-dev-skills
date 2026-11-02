# ============================================================
# File      : test_sync_adapters.py
# Deskripsi : Pengujian tools/sync_adapters.py pada salinan kecil repo,
#             agar .agents/ dan .claude/ milik repo asli tidak tersentuh.
# ============================================================

import os
import shutil
import subprocess
import sys

import pytest
from conftest import REPO, next_line


@pytest.fixture
def fake_repo(tmp_path):
    """
    Menyalin bagian repo yang dibutuhkan sync_adapters ke folder sementara.

    I.S. : tmp_path kosong.
    F.S. : tmp_path berisi skills/, tools/, audit/, config/.
    """
    for name in ("skills", "tools", "audit", "config"):
        shutil.copytree(REPO / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__"))

    return tmp_path


def run_sync(root):
    """
    Menjalankan salinan sync_adapters.py --copy di root.

    I.S. : root adalah repo tiruan dari fake_repo.
    F.S. : CompletedProcess dikembalikan.
    """
    return subprocess.run(
        [sys.executable, str(root / "tools" / "sync_adapters.py"), "--copy"],
        cwd=root,
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


def test_sync_adapters_writes_codex_copies_only(fake_repo):
    res = run_sync(fake_repo)

    assert res.returncode == 0, res.stdout + res.stderr
    assert next_line(res) == "NEXT: adapters synced"
    assert (fake_repo / ".agents" / "skills" / "web-build" / "SKILL.md").is_file()
    assert (fake_repo / ".agents" / "skills" / "web-design" / "SKILL.md").is_file()
    assert not (fake_repo / ".claude").exists()


def test_sync_adapters_warns_on_stale_claude_copy(fake_repo):
    (fake_repo / ".claude" / "skills" / "web-build").mkdir(parents=True)

    res = run_sync(fake_repo)

    assert res.returncode == 0
    assert ".claude/skills/web-build" in res.stdout


def test_sync_adapters_warns_on_claude_md(fake_repo):
    (fake_repo / "CLAUDE.md").write_text("# Test\n", encoding="utf-8")

    res = run_sync(fake_repo)

    assert res.returncode == 0
    assert "PERINGATAN: CLAUDE.md ditemukan" in res.stdout


@pytest.mark.skipif(os.name == "nt", reason="symlink butuh Developer Mode di Windows")
def test_global_target_links_skills_that_still_run(fake_repo, tmp_path_factory):
    # Misalnya ~/.gemini/config/skills untuk Antigravity: di luar repo, jadi harus tautan
    target = tmp_path_factory.mktemp("home") / ".gemini" / "config" / "skills"
    res = subprocess.run(
        [sys.executable, str(fake_repo / "tools" / "sync_adapters.py"), "--target", str(target)],
        cwd=fake_repo, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert (target / "web-build").is_symlink()

    # Skrip dipanggil lewat jalur tautan, dari folder kerja yang lain
    work = tmp_path_factory.mktemp("work")
    run = subprocess.run(
        [sys.executable, str(target / "web-build" / "scripts" / "run.py"), "path", "demo"],
        cwd=work, env={**os.environ, "PD_PROJECTS_DIR": ""}, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert f"PROJECT: {work.resolve() / 'demo'}" in run.stdout


def test_copy_to_a_folder_outside_the_repo_is_refused(fake_repo, tmp_path_factory):
    target = tmp_path_factory.mktemp("outside") / "skills"
    res = subprocess.run(
        [sys.executable, str(fake_repo / "tools" / "sync_adapters.py"), "--copy", "--target", str(target)],
        cwd=fake_repo, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )

    assert res.returncode == 1
    assert "drop --copy" in res.stdout
    assert not target.exists()
