# ============================================================
# File      : test_layout.py
# Deskripsi : Pengujian susunan folder proyek: situs di akar proyek, semua
#             file ScaffolDev di .ScaffolDev/, sehingga menghapus folder itu
#             menyisakan situs murni. Juga perpindahan proyek susunan lama.
# ============================================================

import shutil

import pytest
from conftest import FIXTURES, add_git_folder, copy_fixture, run_script

from lib import paths, project

SITE_ENTRIES = {"index.html", "pages", "css", "js", "data", "assets"}


@pytest.fixture
def kopi_built(projects_dir):
    """
    Membangun kopi-senja sampai handoff.

    I.S. : projects_dir kosong.
    F.S. : (folder proyek, folder kerja) dikembalikan.
    """
    work = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])

    for args in (("validate_brief",), ("gaps",), ("pick_direction", "--pick", "dir-2"), ("compile_tokens",), ("scaffold",), ("handoff",)):
        result = run_script(args[0], "kopi-senja", *args[1:])
        assert result.returncode == 0, result.stdout

    return work.parent, work


def test_project_root_holds_only_the_site(kopi_built):
    site, work = kopi_built

    assert {entry.name for entry in site.iterdir()} == SITE_ENTRIES | {".ScaffolDev"}

    for name in ("brief.yaml", "decisions.yaml", "graph.json", "trace.jsonl", "HANDOFF.md", "EXPLAIN.html",
                 "API_CONTRACT.md", "provenance.json", "state.yaml", ".prettierrc.json", "tokens.css"):
        assert (work / name).is_file(), name


def test_removing_scaffoldev_leaves_a_working_site(kopi_built, tmp_path):
    site, _ = kopi_built
    pure = tmp_path / "murni"
    shutil.copytree(site, pure, ignore=shutil.ignore_patterns(".ScaffolDev"))

    assert {entry.name for entry in pure.iterdir()} == SITE_ENTRIES

    for path in pure.rglob("*"):
        if path.is_file() and path.suffix in (".html", ".css", ".js", ".json"):
            assert ".ScaffolDev" not in path.read_text(encoding="utf-8"), path

    index = (pure / "index.html").read_text(encoding="utf-8")
    assert 'href="css/tokens.css"' in index
    assert (pure / "css" / "tokens.css").is_file()


def test_scaffold_force_keeps_work_folder_and_git(kopi_built):
    site, work = kopi_built
    add_git_folder(site)
    (site / "css" / "extra.css").write_text("/* lama */\n", encoding="utf-8")

    result = run_script("scaffold", "kopi-senja", "--force")

    assert result.returncode == 0, result.stdout
    assert (work / "brief.yaml").is_file()
    assert (work / "HANDOFF.md").is_file()
    assert (site / ".git" / "HEAD").is_file()
    assert not (site / "css" / "extra.css").exists()
    assert (site / "index.html").is_file()


@pytest.mark.node
def test_check_snapshot_and_lint_skip_work_folder(kopi_built):
    site, work = kopi_built
    add_git_folder(site)

    result = run_script("check", "kopi-senja")

    assert result.returncode == 0, result.stdout
    snapshot = work / "rounds" / "1" / "site"
    assert (snapshot / "index.html").is_file()
    assert not (snapshot / ".ScaffolDev").exists()
    assert not (snapshot / ".git").exists()

    report = (work / "report.json").read_text(encoding="utf-8")
    assert ".ScaffolDev" not in report
    assert '"site/' not in report


def test_paths_helpers_ignore_work_folder(kopi_built):
    site, work = kopi_built

    assert paths.site_dir(work) == site
    assert paths.has_site_content(site)
    assert all(".ScaffolDev" not in p.parts for p in paths.site_files(site, "*.html"))
    assert paths.site_files(site, "EXPLAIN.html") == []


def test_legacy_project_is_moved_once(projects_dir):
    legacy = projects_dir / "kopi-senja"
    (legacy / "site" / "css").mkdir(parents=True)
    (legacy / "content").mkdir()
    shutil.copyfile(FIXTURES / "kopi-senja" / "brief.yaml", legacy / "brief.yaml")
    shutil.copyfile(FIXTURES / "kopi-senja" / "directions.yaml", legacy / "directions.yaml")
    (legacy / "content" / "id.yaml").write_text("pages: {}\n", encoding="utf-8")
    (legacy / "site" / "index.html").write_text("<!doctype html>\n", encoding="utf-8")
    (legacy / "site" / "css" / "base.css").write_text("/* */\n", encoding="utf-8")

    result = run_script("validate_brief", "kopi-senja")

    assert result.returncode == 0, result.stdout
    assert {e.name for e in legacy.iterdir()} == {".ScaffolDev", "index.html", "css"}
    assert {e.name for e in (legacy / ".ScaffolDev").iterdir()} >= {"brief.yaml", "directions.yaml", "content", "state.yaml"}
    assert project.migrate_legacy(legacy) is False


def test_new_project_is_not_touched_by_migration(projects_dir):
    work = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml"])

    assert project.migrate_legacy(work.parent) is False
    assert [e.name for e in work.parent.iterdir()] == [".ScaffolDev"]
