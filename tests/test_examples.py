# ============================================================
# File      : test_examples.py
# Deskripsi : Contoh klinik-senyum-sehat disusun dengan prosedur web-design:
#             tes ini menjaga agar contoh tetap lolos dan tetap mengikuti
#             heuristiknya (filter formalitas, sebaran gaya dan peluang,
#             pola yang bisa diisi brief).
# ============================================================

import yaml
from conftest import FIXTURES, REPO, copy_fixture, run_script

from lib import io, project

INDEX = {s["id"]: s for s in yaml.safe_load((REPO / "skills" / "web-design" / "styles" / "index.yaml").read_text(encoding="utf-8"))["styles"]}


def test_clinic_example_follows_the_direction_procedure():
    brief = io.read_yaml(FIXTURES / "klinik-senyum-sehat" / "brief.yaml")
    dirs = io.read_yaml(FIXTURES / "klinik-senyum-sehat" / "directions.yaml")["directions"]
    probs = sorted((d["probability"] for d in dirs), reverse=True)
    site_type = project.load_site_type(brief["site_type"])

    assert {INDEX[d["style"]]["formality"] for d in dirs} <= {"formal", "neutral"}
    assert len({d["style"] for d in dirs}) >= 3
    assert 0.30 <= probs[0] <= 0.40 and 0.05 <= probs[-1] <= 0.12
    assert all(d["register"]["id"] == "Anda" for d in dirs)

    for d in dirs:
        risky = project.layout_risks(brief, site_type, d["layout"])
        assert not risky or d["probability"] <= 0.15, (d["id"], risky)


def test_clinic_example_picks_without_warnings(projects_dir):
    copy_fixture(projects_dir, "klinik-senyum-sehat", ["brief.yaml", "directions.yaml"])

    for name in ("validate_brief", "gaps"):
        assert run_script(name, "klinik-senyum-sehat").returncode == 0

    result = run_script("pick_direction", "klinik-senyum-sehat", "--pick", "dir-1")

    assert result.returncode == 0, result.stdout
    assert "Peringatan" not in result.stdout


def test_deep_mode_example_minutes_follow_the_schema():
    minutes_dir = FIXTURES / "keripik-bu-sari" / "deliberation"
    sittings = sorted(p.stem for p in minutes_dir.glob("*.yaml"))

    assert sittings == ["copy", "direction", "first-page", "site"]
    for sitting in sittings:
        minutes = io.read_yaml(minutes_dir / f"{sitting}.yaml")
        assert project.schema_errors(minutes, "deliberation.schema.json") == [], sitting
        assert minutes["simulated"] is False
        assert len(minutes["rounds"][0]["entries"]) == 5


def test_bilingual_example_copy_has_the_same_shape(tmp_path):
    from lib import audit_rules

    (tmp_path / "content").mkdir()
    for lang in ("id", "en"):
        text = (FIXTURES / "batik-sekar-jagad" / f"content-{lang}.yaml").read_text(encoding="utf-8")
        (tmp_path / "content" / f"{lang}.yaml").write_text(text, encoding="utf-8")

    assert audit_rules.check_bilingual_parity(tmp_path, {"languages": ["id", "en"]}) == []

    # Kalimat yang terpecah koma di list satu baris harus tertangkap
    broken = (tmp_path / "content" / "id.yaml").read_text(encoding="utf-8").replace(
        '- "Di Yogyakarta, Anda bisa melihat batik di mana-mana. Di Sekar Jagad, Anda bisa mencoba membatik tulis sendiri."',
        "- Di Yogyakarta\n          - Anda bisa melihat batik di mana-mana.")
    (tmp_path / "content" / "id.yaml").write_text(broken, encoding="utf-8")
    rules = {f["rule"] for f in audit_rules.check_bilingual_parity(tmp_path, {"languages": ["id", "en"]})}
    assert "bilingual-structure-mismatch" in rules
