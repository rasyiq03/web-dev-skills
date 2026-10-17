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
