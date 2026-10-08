# ============================================================
# File      : handoff.py
# Proyek    : web-skills
# Deskripsi : Menyusun HANDOFF.md, API_CONTRACT.md, dan provenance.json
#             sebagai paket serah terima akhir untuk klien.
# ============================================================

import argparse
import datetime
import re
import sys
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import io, paths, project, report
from lib.report import EXIT_INVALID, fail


def build_api_contract(endpoints_data, mock_dir):
    """
    Menyusun dokumen API_CONTRACT.md dari daftar endpoint dan data mock.

    I.S. : endpoints_data dict {name: {method, path, mock}}; mock_dir path folder mock.
    F.S. : String markdown API_CONTRACT.md dikembalikan.
    """
    lines = [
        "# Kontrak API (API Contract)",
        "",
        "Dokumen ini mendefinisikan bentuk data yang diharapkan oleh antarmuka situs.",
        "Ganti file mock di `site/data/mock/` atau hubungkan backend sungguhan melalui `site/js/api/config.js`.",
        "",
    ]

    if not endpoints_data:
        lines.append("*Tidak ada endpoint data mock yang terdaftar.*")
        return "\n".join(lines) + "\n"

    for ep_name, ep_info in endpoints_data.items():
        method = ep_info.get("method", "GET")
        path = ep_info.get("path", "")
        mock_name = ep_info.get("mock", "")
        lines.append(f"## `{method} {path}`")
        lines.append(f"- **Endpoint Name**: `{ep_name}`")
        lines.append(f"- **Mock File**: `site/data/mock/{mock_name}.mock.json`")

        mock_file = mock_dir / f"{mock_name}.mock.json"
        if mock_file.is_file():
            try:
                m_json = io.read_json(mock_file)
                data_sample = m_json.get("data")
                if isinstance(data_sample, list) and len(data_sample) > 2:
                    sample_display = data_sample[:2]
                else:
                    sample_display = data_sample
                lines.append("```json")
                lines.append(io.to_json(sample_display).strip())
                lines.append("```")
            except Exception:
                lines.append("*(Data mock tidak dapat dibaca)*")
        lines.append("")

    return "\n".join(lines) + "\n"


def build_handoff_md(brief, decisions, gaps, report_summary, placeholders_map):
    """
    Menyusun dokumen HANDOFF.md dalam bahasa pertama brief.

    I.S. : Semua data proyek lengkap.
    F.S. : String markdown HANDOFF.md dikembalikan.
    """
    lang = project.first_language(brief)
    is_id = (lang == "id")
    pname = brief.get("business", {}).get("name", {}).get("value", "Situs")

    chosen_dir_id = decisions.get("direction", "dir-1")
    style_d = next((d for d in decisions.get("decisions", []) if d.get("axis") == "style"), {})
    pal_d = next((d for d in decisions.get("decisions", []) if d.get("axis") == "palette"), {})
    typo_d = next((d for d in decisions.get("decisions", []) if d.get("axis") == "typography"), {})

    # Asumsi: requirements yang inferred + decisions yang sampled
    inferred_reqs = [r for r in gaps.get("requirements", []) if r.get("source") == "inferred"]
    sampled_decs = [d for d in decisions.get("decisions", []) if d.get("source") == "sampled"]

    lines = []
    if is_id:
        lines.append(f"# Ringkasan Serah Terima — {pname}")
        lines.append("")
        lines.append(f"## 1. Arah Visual Terpilih: `{chosen_dir_id}`")
        lines.append(f"- **Gaya Desain**: {style_d.get('choice')} — *{style_d.get('rationale')}*")
        lines.append(f"- **Palet Warna**: {pal_d.get('choice')} — *{pal_d.get('rationale')}*")
        lines.append(f"- **Tipografi**: {typo_d.get('choice')} — *{typo_d.get('rationale')}*")
        lines.append("")
        lines.append("## 2. Asumsi yang Digunakan")
        if inferred_reqs or sampled_decs:
            for r in inferred_reqs:
                lines.append(f"- Fakta inferensi: `{r['id']}` = {r['value']}")
            for d in sampled_decs:
                lines.append(f"- Keputusan tersampel: `{d['id']}` ({d['axis']}) = {d['choice']}")
        else:
            lines.append("- Seluruh data dan keputusan sesuai pernyataan eksplisit dari brief.")
        lines.append("")
        lines.append("## 3. Placeholder yang Perlu Diisi Klien")
        if placeholders_map:
            for fact, ph_text in placeholders_map.items():
                lines.append(f"- `{fact}`: `{ph_text}`")
        else:
            lines.append("- Tidak ada placeholder; seluruh fakta terisi.")
        lines.append("")
        lines.append("## 4. Hasil Uji Otomatis (Quality Gates)")
        lines.append(f"- Error: {report_summary.get('errors', 0)}")
        lines.append(f"- Warning: {report_summary.get('warnings', 0)}")
        lines.append(f"- Kepatuhan Batasan (TFS Auto): {report_summary.get('tfs_auto', 1.0) * 100:.0f}%")
        lines.append(f"- Skor Tanda Tangan Konvensi: {report_summary.get('signature', 1.0) * 100:.0f}%")
        lines.append("- Review semantik aksesibilitas: semantic review skipped")
        lines.append("")
        lines.append("## 5. Cara Pratinjau (Preview)")
        lines.append("Karena situs menggunakan ES Modules (`import`/`export`) dan `fetch()` lokal, halaman tidak dapat dibuka langsung sebagai `file://`.")
        lines.append("Jalankan server HTTP lokal di dalam folder `site/`:")
        lines.append("```bash")
        lines.append("cd site")
        lines.append("python -m http.server 8000")
        lines.append("```")
        lines.append("Buka browser di `http://127.0.0.1:8000`.")
    else:
        lines.append(f"# Site Handoff Report — {pname}")
        lines.append("")
        lines.append(f"## 1. Selected Visual Direction: `{chosen_dir_id}`")
        lines.append(f"- **Style**: {style_d.get('choice')} — *{style_d.get('rationale')}*")
        lines.append(f"- **Palette**: {pal_d.get('choice')} — *{pal_d.get('rationale')}*")
        lines.append(f"- **Typography**: {typo_d.get('choice')} — *{typo_d.get('rationale')}*")
        lines.append("")
        lines.append("## 2. Assumptions Taken")
        if inferred_reqs or sampled_decs:
            for r in inferred_reqs:
                lines.append(f"- Inferred fact: `{r['id']}` = {r['value']}")
            for d in sampled_decs:
                lines.append(f"- Sampled decision: `{d['id']}` ({d['axis']}) = {d['choice']}")
        else:
            lines.append("- All facts and decisions follow stated brief requirements.")
        lines.append("")
        lines.append("## 3. Placeholders to Fill")
        if placeholders_map:
            for fact, ph_text in placeholders_map.items():
                lines.append(f"- `{fact}`: `{ph_text}`")
        else:
            lines.append("- No placeholders remaining.")
        lines.append("")
        lines.append("## 4. Automated Check Scores")
        lines.append(f"- Errors: {report_summary.get('errors', 0)}")
        lines.append(f"- Warnings: {report_summary.get('warnings', 0)}")
        lines.append(f"- TFS Auto Score: {report_summary.get('tfs_auto', 1.0) * 100:.0f}%")
        lines.append(f"- Signature Score: {report_summary.get('signature', 1.0) * 100:.0f}%")
        lines.append("- Accessibility Review: semantic review skipped")
        lines.append("")
        lines.append("## 5. Preview Instructions")
        lines.append("Because the site relies on ES Modules and local fetch, previewing as a raw `file://` URL is blocked by browser CORS.")
        lines.append("Run a local HTTP server from the `site/` folder:")
        lines.append("```bash")
        lines.append("cd site")
        lines.append("python -m http.server 8000")
        lines.append("```")
        lines.append("Open `http://127.0.0.1:8000` in your browser.")

    return "\n".join(lines) + "\n"


# ============================================================
# ========================= HANDOFF ==========================
# ============================================================


def handoff(slug, no_provenance=False):
    """
    Eksekusi serah terima proyek: tulis HANDOFF.md, API_CONTRACT.md, provenance.json.

    I.S. : Proyek memiliki brief, decisions, gaps, site/.
    F.S. : Dokumen handoff tertulis; mencetak ringkasan dan 'NEXT: handoff complete'.
    """
    proj_dir = project.open_project(slug, need=["brief.yaml", "decisions.yaml", "gaps.json"])
    site_dir = proj_dir / "site"
    if not site_dir.is_dir():
        fail(EXIT_INVALID, f"Folder {site_dir} belum ada.", f"run scaffold.py {slug} first")

    brief = io.read_yaml(proj_dir / "brief.yaml")
    decisions = io.read_yaml(proj_dir / "decisions.yaml")
    gaps = io.read_json(proj_dir / "gaps.json")
    state = io.load_state(proj_dir)

    report_path = proj_dir / "report.json"
    report_data = io.read_json(report_path) if report_path.is_file() else {}
    report_summary = report_data.get("summary", state.get("last_summary", {}))

    # 1. Parse endpoints.js
    endpoints_map = {}
    ep_file = site_dir / "js" / "api" / "endpoints.js"
    if ep_file.is_file():
        text = io.read_text(ep_file)
        pattern = re.compile(r"([a-zA-Z0-9_]+)\s*:\s*\{([^}]+)\}")
        for match in pattern.finditer(text):
            ep_name = match.group(1)
            body = match.group(2)
            method = re.search(r"method\s*:\s*['\"]([^'\"]+)['\"]", body)
            path_val = re.search(r"path\s*:\s*['\"]([^'\"]+)['\"]", body)
            mock_val = re.search(r"mock\s*:\s*['\"]([^'\"]+)['\"]", body)
            endpoints_map[ep_name] = {
                "method": method.group(1) if method else "GET",
                "path": path_val.group(1) if path_val else f"/{ep_name}",
                "mock": mock_val.group(1) if mock_val else ep_name,
            }

    # 2. Tulis API_CONTRACT.md
    api_contract_md = build_api_contract(endpoints_map, site_dir / "data" / "mock")
    io.write_text(proj_dir / "API_CONTRACT.md", api_contract_md)

    # 3. Tulis HANDOFF.md
    handoff_md = build_handoff_md(brief, decisions, gaps, report_summary, gaps.get("placeholders", {}))
    io.write_text(proj_dir / "HANDOFF.md", handoff_md)

    # 4. Provenance
    prov_file = proj_dir / "provenance.json"
    if no_provenance:
        if prov_file.is_file():
            prov_file.unlink()
        # Hapus meta generator dari semua file HTML di site/
        for html_f in site_dir.rglob("*.html"):
            h_text = io.read_text(html_f)
            h_cleaned = re.sub(r'[ \t]*<meta name="generator" content="[^"]*"\s*/?>\n?', "", h_text)
            io.write_text(html_f, h_cleaned)
    else:
        site_hashes = {}
        for f in site_dir.rglob("*"):
            if f.is_file():
                rel = f.relative_to(site_dir).as_posix()
                site_hashes[rel] = io.sha256_file(f)

        decisions_hash = io.sha256_file(proj_dir / "decisions.yaml")
        prov_data = {
            "tool": paths.TOOL_NAME,
            "version": paths.VERSION,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "decisions_hash": decisions_hash,
            "files": site_hashes,
        }
        io.write_json(prov_file, prov_data)

    io.save_state(proj_dir, step="handoff")

    lines = [
        f"Serah terima selesai untuk proyek '{slug}':",
        "  - HANDOFF.md berhasil dibuat",
        "  - API_CONTRACT.md berhasil disusun",
    ]
    if no_provenance:
        lines.append("  - provenance.json dilewati (--no-provenance), generator meta tag dibersihkan")
    else:
        lines.append(f"  - provenance.json tercatat ({len(site_hashes)} file di-hash)")

    lines.append("")
    lines.append("=== ISI HANDOFF.MD ===")
    lines.extend(handoff_md.strip().splitlines())

    return lines, "handoff complete"


def main():
    parser = argparse.ArgumentParser(description="Susun paket serah terima proyek.")
    parser.add_argument("slug", help="Slug proyek")
    parser.add_argument("--no-provenance", action="store_true", help="Lewati pembuatan provenance.json")

    args = parser.parse_args()
    return handoff(args.slug, no_provenance=args.no_provenance)


if __name__ == "__main__":
    report.run(main)
