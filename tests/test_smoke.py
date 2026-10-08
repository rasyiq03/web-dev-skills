# ============================================================
# File      : test_smoke.py
# Deskripsi : Memastikan lingkungan tes siap: dependensi Python
#             terpasang dan alat Node dari npm run setup tersedia.
# ============================================================

import importlib

import pytest

from conftest import REPO


@pytest.mark.parametrize("module", ["yaml", "jsonschema", "bs4", "tinycss2"])
def test_python_dependency_importable(module):
    importlib.import_module(module)


@pytest.mark.parametrize(
    "package",
    ["prettier", "eslint", "stylelint", "html-validate", "stylelint-order", "chart.js"],
)
def test_node_tool_installed(package):
    assert (REPO / "node_modules" / package / "package.json").is_file(), "jalankan npm run setup"


def test_projects_dir_fixture(projects_dir, monkeypatch):
    import os

    assert os.environ["PD_PROJECTS_DIR"] == str(projects_dir)
    assert projects_dir.is_relative_to(REPO)

