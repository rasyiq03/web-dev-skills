# ============================================================
# File      : conftest.py
# Deskripsi : Fixture bersama untuk semua tes: folder proyek sementara,
#             salinan fixture kopi-senja, dan pemanggil skrip.
# ============================================================

import os
import shutil
import stat
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
# ======================== OPSI PYTEST =======================
# ============================================================


def pytest_addoption(parser):
    """
    Menambah opsi --network untuk tes yang memasang dependensi dari internet.

    I.S. : parser adalah parser opsi pytest.
    F.S. : Opsi --network tersedia.
    """
    parser.addoption("--network", action="store_true", help="jalankan tes bertanda network")


def pytest_collection_modifyitems(config, items):
    """
    Melewati tes bertanda network kecuali pytest dijalankan dengan --network.

    I.S. : items adalah tes yang terkumpul.
    F.S. : Tes network diberi tanda skip bila --network tidak diberikan.
    """
    if config.getoption("--network"):
        return

    skip = pytest.mark.skip(reason="butuh internet; jalankan dengan --network")

    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)


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

    # File read-only (misalnya objek git tiruan) tidak bisa dihapus rmtree di Windows
    for path in base.rglob("*"):
        if path.is_file():
            path.chmod(stat.S_IREAD | stat.S_IWRITE)
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


def add_git_folder(site_dir):
    """
    Membuat folder .git tiruan di site/, seperti saat pengguna menjadikan site/ repo untuk deploy.

    I.S. : site_dir sudah di-scaffold dan belum punya .git.
    F.S. : site_dir/.git/HEAD ada, dan satu file objek read-only seperti milik git asli.
    """
    git_dir = site_dir / ".git"
    obj = git_dir / "objects" / "ab" / "cdef0123"
    obj.parent.mkdir(parents=True)
    obj.write_text("blob", encoding="utf-8")
    obj.chmod(stat.S_IREAD)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")


def run_script(name, *args, script_dir=SCRIPTS, cwd=REPO):
    """
    Menjalankan satu skrip sebagai proses terpisah, seperti agen memanggilnya.

    I.S. : Variabel lingkungan tes sudah diatur oleh fixture; cwd adalah folder kerja
           (bawaan: root repo).
    F.S. : CompletedProcess dikembalikan; stdout dan stderr berupa teks UTF-8.
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    command = [sys.executable, str(script_dir / f"{name}.py"), *map(str, args)]

    return subprocess.run(
        command,
        cwd=cwd,
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

