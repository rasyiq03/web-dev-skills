# ============================================================
# File      : test_handoff.py
# Deskripsi : Pengujian unit dan CLI untuk handoff.py.
# ============================================================

from conftest import add_git_folder, copy_fixture, next_line, run_script
from lib import io


def test_handoff_provenance_skips_git_folder(projects_dir):
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    run_script("gaps", "kopi-senja")
    run_script("pick_direction", "kopi-senja", "--pick", "dir-2")
    run_script("compile_tokens", "kopi-senja")
    run_script("scaffold", "kopi-senja")
    add_git_folder(proj / "site")

    result = run_script("handoff", "kopi-senja")

    assert result.returncode == 0, result.stderr
    files = io.read_json(proj / "provenance.json")["files"]
    assert "index.html" in files
    assert not [name for name in files if name.startswith(".git/")]


def test_handoff_acceptance(projects_dir):
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    run_script("gaps", "kopi-senja")
    run_script("pick_direction", "kopi-senja", "--pick", "dir-2")
    run_script("compile_tokens", "kopi-senja")
    run_script("scaffold", "kopi-senja")

    result = run_script("handoff", "kopi-senja")
    assert result.returncode == 0, result.stderr
    assert next_line(result) == "NEXT: handoff complete"

    # 1. HANDOFF.md ada dan mencantumkan placeholder
    handoff_file = proj / "HANDOFF.md"
    assert handoff_file.is_file()
    handoff_text = io.read_text(handoff_file)
    assert "dir-2" in handoff_text
    assert "alamat" in handoff_text
    assert "nomor WhatsApp" in handoff_text
    assert "python -m http.server" in handoff_text

    # 2. API_CONTRACT.md ada
    contract_file = proj / "API_CONTRACT.md"
    assert contract_file.is_file()

    # 3. provenance.json mencocokkan hash file
    prov_file = proj / "provenance.json"
    assert prov_file.is_file()
    prov_data = io.read_json(prov_file)
    assert prov_data["tool"] == "pd-web-skills"
    assert prov_data["version"] == "0.1"

    site_dir = proj / "site"
    for rel_path, exp_hash in prov_data["files"].items():
        actual_hash = io.sha256_file(site_dir / rel_path)
        assert actual_hash == exp_hash, f"Hash tidak cocok untuk {rel_path}"

    dec_hash = io.sha256_file(proj / "decisions.yaml")
    assert prov_data["decisions_hash"] == dec_hash


def test_handoff_no_provenance(projects_dir):
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    run_script("gaps", "kopi-senja")
    run_script("pick_direction", "kopi-senja", "--pick", "dir-2")
    run_script("compile_tokens", "kopi-senja")
    run_script("scaffold", "kopi-senja")

    result = run_script("handoff", "kopi-senja", "--no-provenance")
    assert result.returncode == 0

    prov_file = proj / "provenance.json"
    assert not prov_file.exists()

    # Pastikan tag meta generator terhapus dari HTML
    index_html = io.read_text(proj / "site" / "index.html")
    assert '<meta name="generator"' not in index_html
