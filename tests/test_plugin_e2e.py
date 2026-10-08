# ============================================================
# File      : test_plugin_e2e.py
# Deskripsi : Simulasi pengguna baru: hanya isi plugin (tanpa node_modules
#             dan .venv), Python tanpa site-packages, cache kosong, folder
#             kerja kosong; seluruh pipeline lewat run.py harus lolos.
# ============================================================

import json
import os
import shutil
import subprocess
import sys

import pytest
from conftest import REPO, next_line

PLUGIN_DIRS = ("skills", "audit", "config", ".claude-plugin")
PLUGIN_FILES = ("package.json", "package-lock.json", "requirements.txt", "LICENSE")

STEPS = [
    (("path", "kopi-senja"), "NEXT: write the project files in that folder"),
    (("validate_brief", "kopi-senja"), "NEXT: run gaps.py"),
    (("gaps", "kopi-senja"), "NEXT: write directions.yaml (web-design skill)"),
    (("pick_direction", "kopi-senja", "--pick", "dir-2"), "NEXT: run compile_tokens.py"),
    (("compile_tokens", "kopi-senja"), "NEXT: run scaffold.py"),
    (("scaffold", "kopi-senja"), "NEXT: write content/id.yaml (web-build skill step 5)"),
    (("check", "kopi-senja"), "NEXT: run handoff.py"),
    (("handoff", "kopi-senja"), "NEXT: handoff complete"),
]


@pytest.mark.network
def test_fresh_plugin_install_builds_site(tmp_path):
    plugin = tmp_path / "plugin"
    for name in PLUGIN_DIRS:
        shutil.copytree(REPO / name, plugin / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in PLUGIN_FILES:
        shutil.copyfile(REPO / name, plugin / name)

    work = tmp_path / "work"
    (work / "kopi-senja").mkdir(parents=True)
    for name in ("brief.yaml", "directions.yaml"):
        shutil.copyfile(REPO / "examples" / "kopi-senja" / name, work / "kopi-senja" / name)

    env = {k: v for k, v in os.environ.items() if k not in ("PD_PROJECTS_DIR", "PD_NODE_MODULES")}
    env.update(PD_CACHE_DIR=str(tmp_path / "cache"), PD_DATE="2026-10-08", PYTHONIOENCODING="utf-8")
    run_py = plugin / "skills" / "web-build" / "scripts" / "run.py"

    for args, expected in STEPS:
        result = subprocess.run(
            [sys.executable, "-S", str(run_py), *args],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=900,
        )

        assert result.returncode == 0, f"{args}:\n{result.stdout}\n{result.stderr}"
        assert next_line(result) == expected, f"{args}:\n{result.stdout}"

    report = json.loads((work / "kopi-senja" / "report.json").read_text(encoding="utf-8"))
    assert report["summary"]["errors"] == 0
    assert not [f for f in report["findings"] if f["rule"] == "tool-failed"]
    assert (work / "kopi-senja" / "site" / "index.html").is_file()
    assert {p.name.split("-")[0] for p in (tmp_path / "cache").iterdir()} == {"py", "node"}
