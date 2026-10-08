# ============================================================
# File      : test_node_tools.py
# Deskripsi : Pengujian lib/node_tools.lint_config: config linter selalu
#             berada di atas node_modules yang dipakai.
# ============================================================

from conftest import REPO
from lib import node_tools


def test_lint_config_uses_repo_config_with_repo_node_modules(monkeypatch):
    monkeypatch.delenv("PD_NODE_MODULES", raising=False)

    assert node_tools.lint_config("eslint.config.js") == REPO / "config" / "eslint.config.js"


def test_lint_config_copies_next_to_other_node_modules(monkeypatch, tmp_path):
    modules = tmp_path / "node-abc" / "node_modules"
    modules.mkdir(parents=True)
    monkeypatch.setenv("PD_NODE_MODULES", str(modules))

    config = node_tools.lint_config(".stylelintrc.json")

    assert config == tmp_path.resolve() / "node-abc" / "config" / ".stylelintrc.json"
    assert config.read_bytes() == (REPO / "config" / ".stylelintrc.json").read_bytes()
