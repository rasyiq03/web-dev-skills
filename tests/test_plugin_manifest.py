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

    assert market["name"] == "scaffoldev"
    assert plugin["name"] == "scaffoldev"
    assert len(entries) == 1
    assert entries[0]["source"] == "./"


def test_lockfile_root_matches_package_json():
    # Claude Code melewati pemasangan paket plugin bila keduanya berbeda
    package = json.loads((REPO / "package.json").read_text(encoding="utf-8"))
    lock_root = json.loads((REPO / "package-lock.json").read_text(encoding="utf-8"))["packages"][""]

    for field in ("dependencies", "devDependencies"):
        assert lock_root.get(field, {}) == package.get(field, {}), f"jalankan npm install --package-lock-only ({field})"


def test_plugin_icon_is_a_square_png_of_listing_size():
    plugin = json.loads((MANIFEST_DIR / "plugin.json").read_text(encoding="utf-8"))
    icon = (REPO / plugin["icon"]).read_bytes()

    # Kepala PNG: tanda tangan 8 bita lalu chunk IHDR berisi lebar dan tinggi
    assert icon[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = int.from_bytes(icon[16:20], "big"), int.from_bytes(icon[20:24], "big")
    assert width == height and 512 <= width <= 2048
    assert len(icon) < 2 * 1024 * 1024


def test_codex_manifest_matches_the_claude_manifest():
    claude = json.loads((MANIFEST_DIR / "plugin.json").read_text(encoding="utf-8"))
    codex = json.loads((REPO / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))

    # Satu rilis, satu versi: kedua aplikasi menyimpan cache plugin menurut versinya
    for key in ("name", "version", "description", "license", "homepage", "repository"):
        assert codex[key] == claude[key], key

    assert (REPO / codex["skills"] / "web-build" / "SKILL.md").is_file()
    assert (REPO / codex["interface"]["composerIcon"]).is_file()
    assert codex["interface"]["displayName"] == "ScaffolDev"
