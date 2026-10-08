# ============================================================
# File      : test_gaps.py
# Deskripsi : Pengujian unit dan CLI untuk gaps.py.
# ============================================================

from conftest import next_line, run_script
from lib import io


def test_gaps_kopi_senja_acceptance(kopi):
    result = run_script("gaps", "kopi-senja")
    assert result.returncode == 0, result.stderr
    assert next_line(result) == "NEXT: write directions.yaml (web-design skill)"

    gaps_file = kopi / "gaps.json"
    assert gaps_file.is_file()
    gaps = io.read_json(gaps_file)

    # 8 placeholders yang disyaratkan
    expected_placeholders = [
        "address",
        "whatsapp",
        "email",
        "hours",
        "services",
        "founded_year",
        "client_names",
        "team_members",
    ]
    for p in expected_placeholders:
        assert p in gaps["placeholders"], f"Placeholder {p} tidak ditemukan"

    # Requirement ids termasuk req-business.cultural_context
    req_ids = [r["id"] for r in gaps["requirements"]]
    assert "req-business.cultural_context" in req_ids
    assert "req-business.name" in req_ids
    assert "req-audience" in req_ids

    # Batas maksimal pertanyaan
    assert len(gaps["questions"]) <= 6


def test_gaps_interactive_mode(kopi):
    brief_file = kopi / "brief.yaml"
    brief = io.read_yaml(brief_file)
    brief["interactive"] = True
    io.write_yaml(brief_file, brief)

    result = run_script("gaps", "kopi-senja")
    assert result.returncode == 0
    assert next_line(result) == "NEXT: run serve.py"
