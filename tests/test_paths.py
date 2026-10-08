# ============================================================
# File      : test_paths.py
# Deskripsi : Pengujian lib/paths.py: pencarian akar repo, folder
#             node_modules, dan aturan folder proyek.
# ============================================================

import pytest
from conftest import REPO, next_line, run_script
from lib import paths


def make_repo_markers(root):
    """
    Membuat penanda akar repo (audit/ dan config/) di folder tiruan.

    I.S. : root adalah folder kosong.
    F.S. : root/audit/anti-slop.yaml dan root/config/eslint.config.js ada.
    """
    (root / "audit").mkdir(parents=True)
    (root / "audit" / "anti-slop.yaml").write_text("rules: []\n", encoding="utf-8")
    (root / "config").mkdir()
    (root / "config" / "eslint.config.js").write_text("export default [];\n", encoding="utf-8")


def test_find_repo_root_from_codex_copy(tmp_path):
    make_repo_markers(tmp_path)
    lib_dir = tmp_path / ".agents" / "skills" / "web-build" / "scripts" / "lib"
    lib_dir.mkdir(parents=True)

    assert paths.find_repo_root(lib_dir) == tmp_path.resolve()


def test_find_repo_root_without_markers_raises(tmp_path):
    with pytest.raises(RuntimeError):
        paths.find_repo_root(tmp_path)


def test_node_modules_dir_follows_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PD_NODE_MODULES", str(tmp_path))

    assert paths.node_modules_dir() == tmp_path


def test_node_modules_dir_defaults_to_repo(monkeypatch):
    monkeypatch.delenv("PD_NODE_MODULES", raising=False)

    assert paths.node_modules_dir() == REPO / "node_modules"


def test_project_dir_is_in_working_folder_outside_repo(monkeypatch, tmp_path):
    monkeypatch.delenv("PD_PROJECTS_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    assert paths.project_dir("kopi-senja") == tmp_path.resolve() / "kopi-senja"


def test_project_dir_is_under_projects_in_repo(monkeypatch):
    # Sudah lolos sebelum perubahan; menjaga aturan mode pengembangan
    monkeypatch.delenv("PD_PROJECTS_DIR", raising=False)
    monkeypatch.chdir(REPO)

    assert paths.project_dir("kopi-senja") == REPO / "projects" / "kopi-senja"


def test_project_dir_env_wins_over_working_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("PD_PROJECTS_DIR", str(tmp_path))
    monkeypatch.chdir(REPO)

    assert paths.project_dir("kopi-senja") == tmp_path / "kopi-senja"


def test_missing_project_names_absolute_brief_path(projects_dir):
    result = run_script("validate_brief", "belum-ada")

    assert result.returncode == 1
    assert next_line(result) == f"NEXT: write {projects_dir / 'belum-ada' / 'brief.yaml'} first"
