# ============================================================
# File      : conftest.py
# Deskripsi : Fixture bersama untuk semua tes: folder proyek sementara,
#             salinan fixture kopi-senja, dan pemanggil skrip.
# ============================================================

import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

# ============================================================
# ========================== LOKASI ==========================
# ============================================================

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "skills" / "web-build" / "scripts"
TOOLS = REPO / "tools"
FIXTURES = REPO / "examples"
TEST_DATE = "2026-10-08"

# Agar tes unit bisa mengimpor lib/ dan modul skrip secara langsung.
sys.path.insert(0, str(SCRIPTS))


# ============================================================
# ========================= FIXTURE ==========================
# ============================================================


@pytest.fixture
def projects_dir(monkeypatch):
    """
    Menyediakan folder projects/ sementara di dalam repo.

    I.S. : Belum ada folder proyek untuk tes ini.
    F.S. : PD_PROJECTS_DIR menunjuk folder baru di .tmp-tests/; folder dihapus setelah tes.
           Folder sengaja di dalam repo agar Node menemukan node_modules milik repo.
    """
    base = REPO / ".tmp-tests" / uuid.uuid4().hex[:10]
    base.mkdir(parents=True)
    monkeypatch.setenv("PD_PROJECTS_DIR", str(base))
    monkeypatch.setenv("PD_DATE", TEST_DATE)
    yield base
    shutil.rmtree(base, ignore_errors=True)


@pytest.fixture
def kopi(projects_dir):
    """
    Menyalin brief kopi-senja ke folder proyek sementara.

    I.S. : projects_dir kosong.
    F.S. : projects_dir/kopi-senja/brief.yaml ada; path folder proyek dikembalikan.
    """
    return copy_fixture(projects_dir, "kopi-senja", ["brief.yaml"])


# ============================================================
# ========================== HELPER ==========================
# ============================================================


def copy_fixture(projects_dir, name, files):
    """
    Menyalin sebagian file fixture examples/<name>/ ke projects_dir/<name>/.

    I.S. : examples/<name>/ berisi file yang diminta.
    F.S. : File tersalin; path folder proyek dikembalikan.
    """
    target = projects_dir / name
    target.mkdir(parents=True, exist_ok=True)

    for file in files:
        shutil.copyfile(FIXTURES / name / file, target / file)

    return target


def run_script(name, *args, script_dir=SCRIPTS):
    """
    Menjalankan satu skrip sebagai proses terpisah dari root repo, seperti agen memanggilnya.

    I.S. : Variabel lingkungan tes sudah diatur oleh fixture.
    F.S. : CompletedProcess dikembalikan; stdout dan stderr berupa teks UTF-8.
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    command = [sys.executable, str(script_dir / f"{name}.py"), *map(str, args)]

    return subprocess.run(
        command,
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )


def run_tool(name, *args):
    """
    Menjalankan satu alat di tools/ dari root repo.

    I.S. : tools/<name>.py ada.
    F.S. : CompletedProcess dikembalikan.
    """
    return run_script(name, *args, script_dir=TOOLS)


def next_line(result):
    """
    Mengambil baris NEXT: terakhir dari keluaran skrip.

    I.S. : result adalah CompletedProcess dari run_script.
    F.S. : Isi baris NEXT: dikembalikan, atau string kosong bila tidak ada.
    """
    lines = [line for line in result.stdout.splitlines() if line.startswith("NEXT:")]

    return lines[-1] if lines else ""

