# ============================================================
# File      : test_deps.py
# Deskripsi : Pengujian lib/deps.py: lokasi cache, pemakaian dependensi
#             yang sudah ada, kegagalan yang jelas, dan pemasangan sekali
#             ke cache (bertanda network).
# ============================================================

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO, SCRIPTS
from lib import deps
from lib.report import ScriptExit


@pytest.fixture
def stand_in_repo(tmp_path):
    """
    Menyiapkan repo tiruan yang hanya berisi file dependensi, tanpa node_modules.

    I.S. : tmp_path kosong.
    F.S. : tmp_path/plugin berisi package.json, package-lock.json, requirements.txt.
    """
    root = tmp_path / "plugin"
    root.mkdir()

    for name in ("package.json", "package-lock.json", "requirements.txt"):
        shutil.copyfile(REPO / name, root / name)

    return root


def python_only_path():
    """
    Menyusun PATH yang hanya berisi folder Python, tanpa node dan npm.

    I.S. : -
    F.S. : String PATH dikembalikan.
    """
    return str(Path(sys.executable).parent)


def test_cache_root_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("PD_CACHE_DIR", str(tmp_path))

    assert deps.cache_root() == tmp_path


@pytest.mark.skipif(os.name != "nt", reason="aturan Windows")
def test_cache_root_windows_default(monkeypatch, tmp_path):
    monkeypatch.delenv("PD_CACHE_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert deps.cache_root() == tmp_path / "web-skills"


@pytest.mark.skipif(os.name == "nt", reason="aturan POSIX")
def test_cache_root_posix_default(monkeypatch, tmp_path):
    monkeypatch.delenv("PD_CACHE_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    assert deps.cache_root() == tmp_path / "web-skills"


def test_python_packages_already_importable_need_no_cache(tmp_path):
    assert deps.ensure_python_packages(REPO, tmp_path) is None
    assert list(tmp_path.iterdir()) == []


def test_node_tools_use_complete_repo_node_modules(tmp_path):
    assert deps.ensure_node_tools(REPO, tmp_path) == REPO / "node_modules"
    assert list(tmp_path.iterdir()) == []


def test_node_tools_without_node_fail_with_message(stand_in_repo, tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    monkeypatch.setenv("PATH", python_only_path())

    with pytest.raises(ScriptExit) as stop:
        deps.ensure_node_tools(stand_in_repo, cache)

    assert stop.value.code == 1
    assert "Node.js" in "\n".join(stop.value.lines)
    assert not cache.exists()


def test_failed_install_leaves_no_cache_folder(tmp_path):
    final = tmp_path / "cache" / "py-x"
    failing = [sys.executable, "-c", "import sys; sys.exit(3)"]

    with pytest.raises(ScriptExit) as stop:
        deps.install_into(final, "contoh", lambda tmp: subprocess.run(failing, capture_output=True, text=True))

    assert stop.value.code == 1
    assert list((tmp_path / "cache").iterdir()) == []


@pytest.mark.network
def test_node_tools_install_into_cache_once(stand_in_repo, tmp_path, monkeypatch):
    cache = tmp_path / "cache"

    modules = deps.ensure_node_tools(stand_in_repo, cache)

    assert (modules / "eslint" / "package.json").is_file()
    assert modules.parent.parent == cache

    # Panggilan kedua tanpa node/npm di PATH harus memakai cache tanpa memasang ulang
    monkeypatch.setenv("PATH", python_only_path())
    assert deps.ensure_node_tools(stand_in_repo, cache) == modules


@pytest.mark.network
def test_python_packages_install_into_cache_once(stand_in_repo, tmp_path):
    cache = tmp_path / "cache"
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "from pathlib import Path; from lib import deps;"
        "target = deps.ensure_python_packages(Path(sys.argv[2]), Path(sys.argv[3]));"
        "import yaml, jsonschema, bs4, tinycss2; print(target)"
    )

    def run_probe():
        """
        Menjalankan probe di Python tanpa site-packages (-S).

        I.S. : -
        F.S. : CompletedProcess dikembalikan.
        """
        return subprocess.run(
            [sys.executable, "-S", "-c", probe, str(SCRIPTS), str(stand_in_repo), str(cache)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600,
        )

    first = run_probe()
    assert first.returncode == 0, first.stdout + first.stderr
    target = Path(first.stdout.strip().splitlines()[-1])
    assert target.parent == cache
    (target / "sentinel").write_text("x", encoding="utf-8")

    second = run_probe()
    assert second.returncode == 0, second.stdout + second.stderr
    assert Path(second.stdout.strip().splitlines()[-1]) == target
    assert (target / "sentinel").is_file()
