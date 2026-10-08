# ============================================================
# File      : test_plugin_manifest.py
# Deskripsi : Pengujian manifest plugin Claude Code dan marketplace:
#             lolos claude plugin validate --strict dan saling cocok.
# ============================================================

import json
import shutil
import subprocess

import pytest
from conftest import REPO

CLAUDE = shutil.which("claude")
MANIFEST_DIR = REPO / ".claude-plugin"

needs_claude = pytest.mark.skipif(CLAUDE is None, reason="Claude Code CLI tidak terpasang")


def validate(manifest):
    """
    Menjalankan claude plugin validate --strict --json pada satu manifest.

    I.S. : CLAUDE menunjuk CLI Claude Code.
    F.S. : (kode keluar, stdout) dikembalikan.
    """
    result = subprocess.run(
        [CLAUDE, "plugin", "validate", "--strict", "--json", str(manifest)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )

    return result.returncode, result.stdout


@needs_claude
def test_plugin_manifest_passes_strict_validation():
    code, out = validate(MANIFEST_DIR / "plugin.json")

    assert code == 0, out
    assert json.loads(out)["manifest"]["type"] == "plugin"


@needs_claude
def test_marketplace_manifest_passes_strict_validation():
    code, out = validate(MANIFEST_DIR / "marketplace.json")

    assert code == 0, out
    assert json.loads(out)["manifest"]["type"] == "marketplace"


def test_marketplace_installs_this_repository_as_the_plugin():
    plugin = json.loads((MANIFEST_DIR / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((MANIFEST_DIR / "marketplace.json").read_text(encoding="utf-8"))

    entries = [entry for entry in market["plugins"] if entry["name"] == plugin["name"]]

    assert market["name"] == "web-dev-skills"
    assert plugin["name"] == "web-skills"
    assert len(entries) == 1
    assert entries[0]["source"] == "./"
