# ============================================================
# File      : test_dashboard.py
# Deskripsi : Smoke test end-to-end tipe situs dashboard: brief dashboard,
#             scaffolding dengan file khusus dashboard, lapisan mock endpoint,
#             uji ketiadaan fetch langsung, dan check.py dengan 0 error.
# ============================================================

import re
import pytest
from conftest import next_line, run_script
from lib import io


@pytest.mark.node
def test_dashboard_end_to_end_smoke(projects_dir):
    dash_dir = projects_dir / "analytics-demo"
    dash_dir.mkdir(parents=True, exist_ok=True)

    # 1. Buat brief dashboard
    brief_data = {
        "slug": "analytics-demo",
        "site_type": "dashboard",
        "languages": ["id"],
        "interactive": False,
        "business": {
            "name": {"value": "Demo Analytics", "source": "stated"},
            "kind": {"value": "SaaS Dashboard", "source": "stated"},
            "location": {"value": "Jakarta", "source": "stated"},
        },
        "audience": {"value": "Product Managers", "source": "stated"},
        "goal": {"value": "Pantau metrik produk harian", "source": "stated"},
        "tone": {"value": "lugas-profesional", "source": "stated"},
        "facts": {
            "metrics": {"value": "pengguna aktif, pendapatan, churn", "source": "stated"},
            "data_source": {"value": "unknown", "source": "unknown"},
            "time_range": {"value": "30 hari terakhir", "source": "stated"},
            "entities": {"value": "unknown", "source": "unknown"},
            "user_roles": {"value": "unknown", "source": "unknown"},
        },
    }
    io.write_yaml(dash_dir / "brief.yaml", brief_data)

    # 2. validate_brief & gaps
    res_v = run_script("validate_brief", "analytics-demo")
    assert res_v.returncode == 0, res_v.stderr

    res_g = run_script("gaps", "analytics-demo")
    assert res_g.returncode == 0, res_g.stderr

    # 3. Buat 5 arah directions.yaml untuk dashboard
    directions_content = """directions:
- id: dir-1
  probability: 0.30
  style: editorial
  palette: ink-on-cream
  type_pairing: fraunces-plex
  layout:
    shell: sidebar-left
    filters: filter-bar
    kpis: kpi-row
    charts: chart-grid-2
    records: table-plain
  motion: low
  tone: tenang-analitis
  register: { id: Anda }
  summary: Dashboard laporan bergaya editorial dengan serif judul.
  rationale:
    style: Gaya editorial cocok untuk laporan bulanan eksekutif produk.
    color: Palet kertas tinta memberikan kesan tenang saat membaca angka.
    typography: Fraunces memberikan karakter resmi pada metrik utama.
    layout: Bilah samping memudahkan navigasi antara ringkasan dan tabel data.
    motion: Transisi halus membantu fokus pada data yang berubah.
    tone: Register formal Anda sesuai untuk pengambil keputusan produk.
  based_on: [req-audience, req-business.name]
- id: dir-2
  probability: 0.25
  style: neobrutalism
  palette: warm-paper
  type_pairing: grotesk-mono
  layout:
    shell: topbar-tabs
    filters: filter-bar
    kpis: kpi-lead
    charts: chart-lead-side
    records: table-dense
  motion: low
  tone: lugas-tegas
  register: { id: kamu }
  summary: Dashboard internal dengan border tebal dan angka mono.
  rationale:
    style: Border tegas memisahkan kartu metrik dengan sangat kontras.
    color: Kertas kraft hangat nyaman dilihat seharian oleh tim produk.
    typography: Angka mono memudahkan perbandingan digit antar kolom.
    layout: Tab atas memaksimalkan ruang horizontal untuk grafik deret waktu.
    motion: Umpan balik klik langsung tanpa jeda animasi lambat.
    tone: Register santai kamu cocok untuk dasbor operasional internal.
  based_on: [req-audience, req-facts.time_range]
- id: dir-3
  probability: 0.20
  style: neobrutalism
  palette: mint-signal
  type_pairing: wide-display
  layout:
    shell: icon-rail
    filters: filter-drawer
    kpis: kpi-ledger
    charts: chart-stack
    records: table-plain
  motion: medium
  tone: aktif-responsif
  register: { id: Anda }
  summary: Monitor sistem dengan rel ikon ramping dan warna sinyal.
  rationale:
    style: Gaya tajam kontras tinggi cocok untuk pemantauan aktif.
    color: Warna mint kobalt memberikan kewaspadaan visual yang tinggi.
    typography: Font display lebar membuat nilai KPI terbaca dari jauh.
    layout: Rel ikon memberikan area terluas untuk visualisasi data.
    motion: Animasi responsif memperjelas perubahan status grafik.
    tone: Nada profesional Anda menjaga wibawa laporan korporat.
  based_on: [req-business.kind]
- id: dir-4
  probability: 0.15
  style: editorial
  palette: forest-ledger
  type_pairing: newsreader-public
  layout:
    shell: sidebar-left
    filters: filter-bar
    kpis: kpi-row
    charts: chart-lead-side
    records: table-dense
  motion: none
  tone: tenang-stabil
  register: { id: Anda }
  summary: Dasbor keuangan hijau ledger dengan tipografi koran klasik.
  rationale:
    style: Tampilan buku kas hijau mencerminkan stabilitas finansial.
    color: Hijau ledger cocok dengan pembacaan metrik pendapatan.
    typography: Newsreader memberikan keterbacaan tinggi pada tabel padat.
    layout: Tata letak kolom ganda menonjolkan tren pendapatan utama.
    motion: Tanpa gerak untuk menghindari distraksi saat analisis angka.
    tone: Bahasa lugas Anda menjaga fokus tim finansial dan produk.
  based_on: [req-facts.metrics]
- id: dir-5
  probability: 0.10
  style: editorial
  palette: night-print
  type_pairing: instrument-familjen
  layout:
    shell: topbar-tabs
    filters: filter-drawer
    kpis: kpi-ledger
    charts: chart-grid-2
    records: table-plain
  motion: low
  tone: gelap-fokus
  register: { id: kamu }
  summary: Mode gelap elegan dengan kontras kuningan untuk ruang kendali.
  rationale:
    style: Tema gelap ramah mata untuk analisis metrik di malam hari.
    color: Latar gelap dengan aksen kuningan menonjolkan titik data penting.
    typography: Angka proporsional ramping menghemat ruang tabel.
    layout: Panel grid 2 kolom membagi metrik secara seimbang.
    motion: Transisi halus pada laci filter menjaga konteks tampilan.
    tone: Nada bersahabat kamu cocok untuk startup teknologi modern.
  based_on: [req-audience, req-business.location]
"""
    io.write_text(dash_dir / "directions.yaml", directions_content)

    # 4. pick_direction, compile_tokens, scaffold
    res_p = run_script("pick_direction", "analytics-demo", "--pick", "dir-2")
    assert res_p.returncode == 0, res_p.stderr

    res_c = run_script("compile_tokens", "analytics-demo")
    assert res_c.returncode == 0, res_c.stderr

    res_s = run_script("scaffold", "analytics-demo")
    assert res_s.returncode == 0, res_s.stderr

    site_dir = dash_dir / "site"

    # Verifikasi file khusus dashboard dibuat
    assert (site_dir / "js" / "charts.js").is_file()
    assert (site_dir / "js" / "table.js").is_file()
    assert (site_dir / "js" / "filters.js").is_file()
    assert (site_dir / "js" / "vendor" / "chart.umd.js").is_file()

    # Verifikasi label mock pada halaman data (index.html dan pages/data.html)
    index_html = io.read_text(site_dir / "index.html")
    assert "data-pd-mock-label" in index_html
    data_html = io.read_text(site_dir / "pages" / "data.html")
    assert "data-pd-mock-label" in data_html

    # 5. Pasang 1 endpoint dan 1 mock valid
    ep_file = site_dir / "js" / "api" / "endpoints.js"
    io.write_text(
        ep_file,
        """/* ============================================================
 * File      : endpoints.js
 * Proyek    : Demo Analytics
 * Deskripsi : Endpoint data dashboard
 * Dibuat    : sistem skill website 0.1, 2026-10-08
 * ============================================================ */

export const ENDPOINTS = {
\tmetrics: { method: 'GET', path: '/metrics', mock: 'metrics' },
};
""",
    )

    mock_file = site_dir / "data" / "mock" / "metrics.mock.json"
    io.write_json(
        mock_file,
        {
            "_mock": True,
            "endpoint": "GET /metrics",
            "generated_by": "pd-web-skills 0.1",
            "data": [
                {"date": "2026-10-01", "users": 1200, "revenue": 50000000},
                {"date": "2026-10-02", "users": 1250, "revenue": 52000000},
            ],
        },
    )

    # 6. Pastikan tidak ada pemanggilan fetch() langsung di luar client.js
    for js_path in (site_dir / "js").rglob("*.js"):
        if "client.js" in js_path.name or "vendor" in js_path.as_posix():
            continue
        text = io.read_text(js_path)
        assert not re.search(r"\bfetch\(", text), f"fetch() ditemukan di {js_path}"

    # 7. Jalankan check.py -> harus 0 error
    res_chk = run_script("check", "analytics-demo")
    assert res_chk.returncode == 0, res_chk.stderr
    assert next_line(res_chk) == "NEXT: run handoff.py"

    report_data = io.read_json(dash_dir / "report.json")
    assert report_data["summary"]["errors"] == 0

    # 8. Jalankan handoff.py -> API_CONTRACT.md berisi /metrics
    res_h = run_script("handoff", "analytics-demo")
    assert res_h.returncode == 0, res_h.stderr

    contract_text = io.read_text(dash_dir / "API_CONTRACT.md")
    assert "GET /metrics" in contract_text
