# ============================================================
# File      : test_skill_text.py
# Deskripsi : Pengujian rujukan di SKILL.md: setiap path plugin ada, dan
#             setiap perintah python lewat run.py dengan perintah yang sah.
# ============================================================

import re

import run
from conftest import REPO

SKILL_FILES = [REPO / "skills" / "web-build" / "SKILL.md", REPO / "skills" / "web-design" / "SKILL.md"]
ROOT_REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s`\"')]+)")
COMMAND = re.compile(r"`python ([^`]+)`")
RUN = '"${CLAUDE_PLUGIN_ROOT}/skills/web-build/scripts/run.py"'


def test_every_plugin_root_path_exists():
    for skill in SKILL_FILES:
        for ref in ROOT_REF.findall(skill.read_text(encoding="utf-8")):
            ref = ref.rstrip(".,;:")
            pattern = re.sub(r"<[^>]+>", "*", ref)

            assert list(REPO.glob(pattern)), f"{skill.parent.name}/SKILL.md: {ref} tidak ada"


def test_every_python_command_goes_through_run_py():
    valid = {"path", *run.SCRIPTS}
    commands = []

    for skill in SKILL_FILES:
        commands += COMMAND.findall(skill.read_text(encoding="utf-8"))

    assert commands, "SKILL.md tidak memuat perintah python"

    for command in commands:
        assert command.startswith(RUN + " "), command
        assert command[len(RUN) + 1:].split()[0] in valid, command
