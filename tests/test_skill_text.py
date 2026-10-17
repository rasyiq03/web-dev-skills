# ============================================================
# File      : test_skill_text.py
# Deskripsi : Pengujian rujukan di SKILL.md: setiap path plugin ada, perintah
#             lengkap run.py tertulis, dan setiap singkatan `run <skrip>` sah.
# ============================================================

import re

import run
from conftest import REPO

SKILL_FILES = [
    REPO / "skills" / "web-build" / "SKILL.md",
    REPO / "skills" / "web-design" / "SKILL.md",
    REPO / "skills" / "web-build" / "references" / "mode-guided.md",
]
ROOT_REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s`\"')]+)")
COMMAND = re.compile(r"`python ([^`]+)`")
SHORTHAND = re.compile(r"`run ([a-z_]+)[ `]")
RUN = '"${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py"'
FULL_FORM = f"`python {RUN} <script> <slug>`"


def test_every_plugin_root_path_exists():
    for skill in SKILL_FILES:
        for ref in ROOT_REF.findall(skill.read_text(encoding="utf-8")):
            ref = ref.rstrip(".,;:")
            pattern = re.sub(r"<[^>]+>", "*", ref)

            assert list(REPO.glob(pattern)), f"{skill.parent.name}/SKILL.md: {ref} tidak ada"


def test_every_python_command_goes_through_run_py():
    for skill in SKILL_FILES:
        for command in COMMAND.findall(skill.read_text(encoding="utf-8")):
            assert command.startswith(RUN + " "), command


def test_web_build_defines_run_shorthand_once():
    text = SKILL_FILES[0].read_text(encoding="utf-8")

    assert text.count(FULL_FORM) == 1, "web-build/SKILL.md harus menulis perintah lengkap run.py sekali"
    assert "`run <script> <slug>` is short for that command" in text


def test_every_run_shorthand_names_a_real_script():
    valid = {"path", *run.SCRIPTS}
    names = []

    for skill in SKILL_FILES:
        names += SHORTHAND.findall(skill.read_text(encoding="utf-8"))

    assert names, "SKILL.md tidak memuat perintah run"

    for name in names:
        assert name in valid, f"run {name} bukan skrip run.py"
