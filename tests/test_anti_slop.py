# ============================================================
# File      : test_anti_slop.py
# Deskripsi : Pengujian kepatuhan aturan anti-slop dari audit/anti-slop.yaml:
#             - unsourced-number
#             - cliche-phrase
#             - placeholder-person
#             - emoji-in-heading
#             - direct-fetch
#             - mock-people-quotes
# ============================================================

import json
from conftest import copy_fixture
from lib import audit_rules, io


def test_anti_slop_rules_execution(projects_dir):
    """
    Memverifikasi bahwa aturan anti-slop mendeteksi pelanggaran yang disengaja.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "decisions.yaml"])
    site_dir = proj / "site"
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "css").mkdir(parents=True, exist_ok=True)
    (site_dir / "js").mkdir(parents=True, exist_ok=True)
    (site_dir / "data" / "mock").mkdir(parents=True, exist_ok=True)

    brief = io.read_yaml(proj / "brief.yaml")
    decisions = io.read_yaml(proj / "decisions.yaml")

    # 1. Buat HTML dengan pelanggaran:
    #    - Angka tanpa sumber: 8888888
    #    - Frasa klise: "solusi terpercaya"
    #    - Placeholder person: "John Doe"
    #    - Emoji di heading: "☕"
    html_content = """<!doctype html>
<html>
<head><title>Test</title></head>
<body>
<main>
    <h2>Menu Kopi ☕</h2>
    <p>Kami adalah solusi terpercaya untuk anda.</p>
    <p>Nama barista kami adalah John Doe.</p>
    <p>Jumlah cabang kami mencapai 8888888 di seluruh dunia.</p>
    <blockquote>Kutipan yang tidak ada di brief sama sekali.</blockquote>
</main>
</body>
</html>
"""
    io.write_text(site_dir / "index.html", html_content)

    # 2. Buat JS dengan direct-fetch
    js_content = """
function loadData() {
    fetch("https://api.example.com/data");
}
"""
    io.write_text(site_dir / "js" / "custom.js", js_content)

    # 3. Buat mock file dengan quote/testimoni
    mock_data = {
        "_mock": True,
        "endpoint": "GET /api/reviews",
        "data": [
            {"id": 1, "testimoni": "Kopi sangat enak!"}
        ]
    }
    io.write_json(site_dir / "data" / "mock" / "reviews.mock.json", mock_data)

    # Jalankan audit_anti_slop
    findings = audit_rules.audit_anti_slop(proj, brief, decisions, {})
    rule_ids = {f["rule"] for f in findings}

    assert "unsourced-number" in rule_ids, "unsourced-number harus terdeteksi"
    assert "cliche-phrase" in rule_ids, "cliche-phrase harus terdeteksi"
    assert "placeholder-person" in rule_ids, "placeholder-person harus terdeteksi"
    assert "emoji-in-heading" in rule_ids, "emoji-in-heading harus terdeteksi"
    assert "direct-fetch" in rule_ids, "direct-fetch harus terdeteksi"
    assert "mock-people-quotes" in rule_ids, "mock-people-quotes harus terdeteksi"
    assert "unsourced-quote" in rule_ids, "unsourced-quote harus terdeteksi"
