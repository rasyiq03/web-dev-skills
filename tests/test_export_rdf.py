# ============================================================
# File      : test_export_rdf.py
# Deskripsi : Pengujian tools/export_rdf.py: model RDF sah terhadap
#             tools/shapes.ttl, dan shape SHACL per batasan sepakat dengan
#             check.py, baik saat situs memenuhi batasan maupun saat dirusak.
# ============================================================

import pytest
from conftest import REPO, copy_fixture, fill_empty_sections, run_script

from lib import io

pytest.importorskip("pyshacl")


@pytest.fixture
def kopi_built(projects_dir):
    work = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    for args in (("gaps",), ("pick_direction", "--pick", "dir-2"), ("compile_tokens",), ("scaffold",)):
        assert run_script(args[0], "kopi-senja", *args[1:]).returncode == 0
    fill_empty_sections(work.parent)
    return work


def export(slug="kopi-senja"):
    return run_script("export_rdf", slug, script_dir=REPO / "tools")


def test_export_writes_turtle_and_agrees_with_check(kopi_built):
    result = export()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Bentuk model terhadap tools/shapes.ttl: sah" in result.stdout
    assert "Berbeda dengan check.py: tidak ada" in result.stdout
    model = (kopi_built / "rdf" / "model.ttl").read_text(encoding="utf-8")
    assert "sd:basedOn" in model and "sd:justifiedBy" in model and "sd:verifiedBy" in model
    assert (kopi_built / "rdf" / "constraints.ttl").is_file()


def test_broken_site_fails_the_same_constraints_in_shacl_and_check(kopi_built):
    site = kopi_built.parent
    kontak = site / "pages" / "kontak.html"
    kontak.write_text(kontak.read_text(encoding="utf-8").replace('data-pd-pattern="contact-card"', 'data-pd-pattern="x"'),
                      encoding="utf-8")
    index = site / "index.html"
    index.write_text(index.read_text(encoding="utf-8").replace("</main>", "<p>Silakan Anda mampir.</p></main>"),
                     encoding="utf-8")

    result = export()

    assert result.returncode == 0, result.stdout
    assert "Batasan gagal menurut SHACL: c-layout-contact, c-register-id" in result.stdout
    assert "Berbeda dengan check.py: tidak ada" in result.stdout


def test_decision_without_a_verifying_constraint_is_not_a_valid_model(kopi_built):
    decisions = io.read_yaml(kopi_built / "decisions.yaml")
    decisions["decisions"][0].pop("verified_by")
    io.write_yaml(kopi_built / "decisions.yaml", decisions)

    result = export()

    assert result.returncode == 2
    assert "TIDAK sah" in result.stdout
