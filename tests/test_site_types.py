# ============================================================
# File      : test_site_types.py
# Deskripsi : Pengujian validasi, analisis gaps, dan scaffolding
#             untuk 3 tipe situs tambahan di milestone v0.2:
#             - landing
#             - portfolio
#             - umkm-catalog
# ============================================================

from conftest import next_line, run_script
from lib import io


def create_minimal_tokens_and_decisions(proj_dir, site_type_id, sections):
    """Membuat file penunjang minimal agar scaffold.py dapat dieksekusi."""
    decisions_yaml = f"""seed: 12345
chosen:
  id: dir-test
  name: Test Direction
  style: editorial
  palette: test
  type_pairing: test
  layout:
{chr(10).join(f'    {s}: test-pattern' for s in sections)}
  motion: low
  register: {{ id: {{ pronoun: kamu }} }}
decisions: []
constraints: []
"""
    io.write_text(proj_dir / "decisions.yaml", decisions_yaml)
    io.write_text(proj_dir / "tokens.css", ":root { --pd-color-ink: #000; --pd-color-paper: #fff; }\n")
    io.write_text(proj_dir / "fonts.html", '<link rel="stylesheet" href="https://fonts.googleapis.com">\n')


def test_landing_site_type(projects_dir):
    """
    Menguji validasi, gaps, dan scaffolding untuk tipe situs landing.
    """
    slug = "kursus-kilat"
    proj = projects_dir / slug
    proj.mkdir(parents=True, exist_ok=True)

    brief_yaml = """slug: kursus-kilat
site_type: landing
languages: [id]
interactive: false
business:
  name: { value: Kursus Kilat Coding, source: stated }
  kind: { value: pelatihan online, source: stated }
  location: { value: unknown, source: unknown }
goal: { value: mendaftar webinar, source: stated }
tone: { value: unknown, source: unknown }
audience: { value: unknown, source: unknown }
facts:
  product_name: { value: unknown, source: unknown }
  price: { value: unknown, source: unknown }
  whatsapp: { value: unknown, source: unknown }
"""
    io.write_text(proj / "brief.yaml", brief_yaml)

    # 1. validate_brief
    res_vb = run_script("validate_brief", slug)
    assert res_vb.returncode == 0, res_vb.stderr
    assert next_line(res_vb) == "NEXT: run gaps.py"

    # 2. gaps
    res_gap = run_script("gaps", slug)
    assert res_gap.returncode == 0, res_gap.stderr
    gaps_data = io.read_json(proj / "gaps.json")
    assert gaps_data["site_type"] == "landing"
    assert gaps_data["placeholders"]["product_name"] == "[[ISI: nama produk]]"
    assert gaps_data["placeholders"]["price"] == "[[ISI: harga]]"

    # 3. scaffold
    create_minimal_tokens_and_decisions(proj, "landing", ["hero", "problem", "offer", "proof", "action"])
    res_scaf = run_script("scaffold", slug)
    assert res_scaf.returncode == 0, res_scaf.stderr

    site_dir = proj / "site"
    assert (site_dir / "index.html").is_file()
    index_html = io.read_text(site_dir / "index.html")
    assert 'data-pd-pattern="test-pattern"' in index_html


def test_portfolio_site_type(projects_dir):
    """
    Menguji validasi, gaps, dan scaffolding untuk tipe situs portfolio.
    """
    slug = "studio-arunika"
    proj = projects_dir / slug
    proj.mkdir(parents=True, exist_ok=True)

    brief_yaml = """slug: studio-arunika
site_type: portfolio
languages: [id]
interactive: false
business:
  name: { value: Arunika Studio, source: stated }
  kind: { value: studio desain grafis, source: stated }
  location: { value: unknown, source: unknown }
audience: { value: art director & brand manager, source: stated }
goal: { value: unknown, source: unknown }
tone: { value: unknown, source: unknown }
facts:
  projects: { value: unknown, source: unknown }
  skills: { value: unknown, source: unknown }
  email: { value: unknown, source: unknown }
"""
    io.write_text(proj / "brief.yaml", brief_yaml)

    # 1. validate_brief
    res_vb = run_script("validate_brief", slug)
    assert res_vb.returncode == 0, res_vb.stderr

    # 2. gaps
    res_gap = run_script("gaps", slug)
    assert res_gap.returncode == 0, res_gap.stderr
    gaps_data = io.read_json(proj / "gaps.json")
    assert gaps_data["site_type"] == "portfolio"
    assert gaps_data["placeholders"]["projects"] == "[[ISI: daftar proyek]]"

    # 3. scaffold
    create_minimal_tokens_and_decisions(
        proj, "portfolio", ["hero", "selected-work", "work-index", "about", "contact"]
    )
    res_scaf = run_script("scaffold", slug)
    assert res_scaf.returncode == 0, res_scaf.stderr

    site_dir = proj / "site"
    assert (site_dir / "index.html").is_file()
    assert (site_dir / "pages" / "karya.html").is_file()
    assert (site_dir / "pages" / "tentang.html").is_file()
    assert (site_dir / "pages" / "kontak.html").is_file()

    # Pastikan data label hadir pada halaman yang memiliki data: true
    index_html = io.read_text(site_dir / "index.html")
    assert "data-pd-mock-label" in index_html


def test_umkm_catalog_site_type(projects_dir):
    """
    Menguji validasi, gaps, dan scaffolding untuk tipe situs umkm-catalog.
    """
    slug = "kripik-singkong-mak-ecih"
    proj = projects_dir / slug
    proj.mkdir(parents=True, exist_ok=True)

    brief_yaml = """slug: kripik-singkong-mak-ecih
site_type: umkm-catalog
languages: [id]
interactive: false
business:
  name: { value: Kripik Singkong Mak Ecih, source: stated }
  kind: { value: produsen makanan ringan, source: stated }
  location: { value: Garut, source: stated }
audience: { value: unknown, source: unknown }
goal: { value: unknown, source: unknown }
tone: { value: unknown, source: unknown }
facts:
  products: { value: unknown, source: unknown }
  prices: { value: unknown, source: unknown }
  whatsapp: { value: unknown, source: unknown }
"""
    io.write_text(proj / "brief.yaml", brief_yaml)

    # 1. validate_brief
    res_vb = run_script("validate_brief", slug)
    assert res_vb.returncode == 0, res_vb.stderr

    # 2. gaps
    res_gap = run_script("gaps", slug)
    assert res_gap.returncode == 0, res_gap.stderr
    gaps_data = io.read_json(proj / "gaps.json")
    assert gaps_data["site_type"] == "umkm-catalog"
    assert gaps_data["placeholders"]["products"] == "[[ISI: daftar produk]]"
    assert gaps_data["placeholders"]["prices"] == "[[ISI: harga produk]]"

    # 3. scaffold
    create_minimal_tokens_and_decisions(
        proj, "umkm-catalog", ["hero", "featured", "catalog", "how-to-order"]
    )
    res_scaf = run_script("scaffold", slug)
    assert res_scaf.returncode == 0, res_scaf.stderr

    site_dir = proj / "site"
    assert (site_dir / "index.html").is_file()
    assert (site_dir / "pages" / "produk.html").is_file()
    assert (site_dir / "pages" / "cara-pesan.html").is_file()
