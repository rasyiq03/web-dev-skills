# ============================================================
# File      : test_sync_adapters.py
# Deskripsi : Pengujian untuk tools/sync_adapters.py.
# ============================================================

from conftest import REPO, next_line, run_tool
from lib import io


def test_sync_adapters_copy_mode():
    res = run_tool("sync_adapters", "--copy")
    assert res.returncode == 0, res.stderr
    assert next_line(res) == "NEXT: adapters synced"

    claude_skills = REPO / ".claude" / "skills"
    agents_skills = REPO / ".agents" / "skills"

    assert (claude_skills / "web-build" / "SKILL.md").is_file()
    assert (claude_skills / "web-design" / "SKILL.md").is_file()
    assert (agents_skills / "web-build" / "SKILL.md").is_file()
    assert (agents_skills / "web-design" / "SKILL.md").is_file()


def test_sync_adapters_warns_on_claude_md(tmp_path):
    claude_md = REPO / "CLAUDE.md"
    try:
        io.write_text(claude_md, "# Test\n")
        res = run_tool("sync_adapters", "--copy")
        assert res.returncode == 0
        assert "PERINGATAN: CLAUDE.md ditemukan" in res.stdout
    finally:
        if claude_md.is_file():
            claude_md.unlink()
