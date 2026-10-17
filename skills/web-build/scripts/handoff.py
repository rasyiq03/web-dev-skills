# ============================================================
# File      : handoff.py
# Proyek    : ScaffolDev
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

from lib import council, explain, guided, io, paths, project, report, signals, trace
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
        "Ganti file mock di `data/mock/` atau hubungkan backend sungguhan melalui `js/api/config.js`.",
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
        lines.append(f"- **Mock File**: `data/mock/{mock_name}.mock.json`")

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


def placeholder_lines(site_ph, unused, favicon, lang):
    """
    Menulis bagian placeholder HANDOFF.md dari isi situs yang sebenarnya.

    I.S. : site_ph adalah hasil project.site_placeholders(); unused adalah {fakta: teks} dari
           gaps.json yang tidak tampil di situs; favicon True bila ikon sementara masih ada.
    F.S. : Daftar baris markdown dikembalikan.
    """
    lines = []

    if site_ph:
        lines.append("Tampil di situs; ganti semuanya sebelum situs dipakai:" if lang == "id"
                     else "Shown on the site; replace every one before the site goes live:")
        lines += [f"- `{text}`: {', '.join(files)}" for text, files in site_ph.items()]
    else:
        lines.append("- Tidak ada placeholder di halaman situs." if lang == "id" else "- No placeholders on the site pages.")

    if favicon:
        lines.append("")
        lines.append("Ikon situs `assets/img/favicon.svg` masih sementara (huruf pertama nama); ganti dengan logo usaha." if lang == "id"
                     else "The site icon `assets/img/favicon.svg` is a stand-in (the first letter of the name); replace it with the real logo.")

    if unused:
        lines.append("")
        lines.append("Fakta yang belum diketahui dan belum dipakai di halaman (isi bila ingin ditambahkan):" if lang == "id"
                     else "Facts still unknown and not used on any page (fill in if you want them added):")
        lines += [f"- `{fact}`: `{text}`" for fact, text in unused.items()]

    return lines


def build_handoff_md(brief, decisions, gaps, report_summary, placeholders):
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
        lines += placeholder_lines(*placeholders, "id")
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
        lines.append("Jalankan server HTTP lokal di folder proyek (folder yang berisi `index.html`):")
        lines.append("```bash")
        lines.append(f"cd {brief.get('slug', '<slug>')}")
        lines.append("python -m http.server 8000")
        lines.append("```")
        lines.append("Buka browser di `http://127.0.0.1:8000`.")
        lines.append("")
        lines.append("## 6. Penjelasan Keputusan")
        lines.append("Buka `EXPLAIN.html` di folder proyek (bisa langsung diklik dua kali, tanpa server dan tanpa internet). Isinya: siapa memutuskan apa, kenapa, dan bagian mana yang ikut berubah bila satu keputusan diganti.")
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
        lines += placeholder_lines(*placeholders, "en")
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
        lines.append("Run a local HTTP server from the project folder (the one with `index.html`):")
        lines.append("```bash")
        lines.append(f"cd {brief.get('slug', '<slug>')}")
        lines.append("python -m http.server 8000")
        lines.append("```")
        lines.append("Open `http://127.0.0.1:8000` in your browser.")
        lines.append("")
        lines.append("## 6. Decision Explanation")
        lines.append("Open `EXPLAIN.html` in the project folder (double-click works, no server or internet needed). It shows who decided what, why, and what changes if a decision is replaced.")

    return "\n".join(lines) + "\n"


# ============================================================
# ========================= HANDOFF ==========================
# ============================================================


def signals_md(proj_dir, brief):
    """
    Menyusun bagian 7 HANDOFF.md: sinyal Agentivism P1-P6 dalam kalimat sederhana.

    I.S. : Proyek punya brief.yaml; trace dan report boleh belum ada.
    F.S. : Teks markdown bagian 7 dikembalikan.
    """
    lang = "id" if project.first_language(brief) == "id" else "en"
    title, intro, items = signals.lines(signals.compute(proj_dir), lang)

    return "\n".join(["", f"## 7. {title}", intro, *[f"- {item}" for item in items]]) + "\n"


def finish_guided(proj_dir, brief):
    """
    Mencatat hasil checkpoint proyek mode terpandu di profil developer.

    I.S. : trace.jsonl berisi peristiwa checkpoint (boleh kosong).
    F.S. : Untuk mode guided: profil diperbarui dan baris ringkasan dikembalikan;
           mode lain: daftar kosong dan profil tidak disentuh.
    """
    if brief.get("mode") != "guided":
        return []

    lang = "id" if project.first_language(brief) == "id" else "en"
    level = guided.project_level(brief)
    results = guided.results_from_trace(trace.read(proj_dir))
    recorded = {name: results.get(name, "skipped") for name in guided.CHECKPOINTS}
    new_level = guided.record_project(str(proj_dir.resolve()), level, recorded)
    states = ", ".join(f"{name} {guided.RESULT_NAMES[lang][result]}" for name, result in recorded.items())

    return [
        f"  - Mode terpandu: tingkat {level} ({guided.LEVEL_NAMES[lang][level]}); checkpoint: {states}",
        f"  - Proyek berikutnya: tingkat {new_level} ({guided.LEVEL_NAMES[lang][new_level]})",
    ]


def finish_deep(proj_dir, brief, report_summary):
    """
    Meringkas sidang dewan dan menyatakan apakah situs siap pakai, khusus mode deep work.

    I.S. : trace.jsonl berisi peristiwa council untuk sidang yang notulennya lolos.
    F.S. : Baris ringkasan dikembalikan; daftar kosong untuk mode lain. "Siap pakai" hanya
           bila keempat sidang tercatat dan check melaporkan nol error dan nol peringatan.
    """
    if brief.get("mode") != "deep":
        return []

    held = {e["sitting"]: e for e in trace.read(proj_dir) if e.get("event") == "council"}
    done = [f"{s} ({held[s]['method']})" for s in council.SITTINGS if s in held]
    missing = [s for s in council.SITTINGS if s not in held]
    simulated = any(e.get("simulated") for e in held.values())
    errors, warnings = report_summary.get("errors", 0), report_summary.get("warnings", 0)
    lines = [f"  - Mode deep work: sidang tercatat {', '.join(done) or 'tidak ada'}"]

    if simulated:
        lines.append("  - Sebagian sidang disimulasikan oleh satu agen (tanpa subagent)")

    if missing or errors or warnings or not report_summary:
        reasons = ([f"sidang belum diadakan: {', '.join(missing)}"] if missing else []) + \
                  ([f"check: {errors} error, {warnings} peringatan"] if (errors or warnings) else []) + \
                  (["check belum dijalankan"] if not report_summary else [])
        lines.append(f"  - Belum siap pakai: {'; '.join(reasons)}")
    else:
        lines.append("  - Siap pakai: keempat sidang mufakat atau voting, check nol error dan nol peringatan; isi placeholder sebelum dipublikasikan")

    return lines


def handoff(slug, no_provenance=False):
    """
    Eksekusi serah terima proyek: tulis HANDOFF.md, API_CONTRACT.md, provenance.json.

    I.S. : Proyek memiliki brief, decisions, gaps, dan situs yang sudah di-scaffold.
    F.S. : Dokumen handoff tertulis; mencetak ringkasan dan 'NEXT: handoff complete'.
    """
    proj_dir = project.open_project(slug, need=["brief.yaml", "decisions.yaml", "gaps.json"])
    site_dir = paths.site_dir(proj_dir)
    if not paths.has_site_content(site_dir):
        fail(EXIT_INVALID, f"Situs di {site_dir} belum ada.", f"run scaffold.py {slug} first")

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
    site_ph = project.site_placeholders(site_dir)
    unused = {fact: text for fact, text in gaps.get("placeholders", {}).items() if text not in site_ph}
    favicon = (site_dir / "assets" / "img" / "favicon.svg").is_file()
    handoff_md = build_handoff_md(brief, decisions, gaps, report_summary, (site_ph, unused, favicon))
    handoff_md += signals_md(proj_dir, brief)
    io.write_text(proj_dir / "HANDOFF.md", handoff_md)

    # 4. Provenance
    prov_file = proj_dir / "provenance.json"
    if no_provenance:
        if prov_file.is_file():
            prov_file.unlink()
        # Hapus meta generator dari semua file HTML situs
        for html_f in paths.site_files(site_dir, "*.html"):
            h_text = io.read_text(html_f)
            h_cleaned = re.sub(r'[ \t]*<meta name="generator" content="[^"]*"\s*/?>\n?', "", h_text)
            io.write_text(html_f, h_cleaned)
    else:
        site_hashes = {}
        for f in site_dir.rglob("*"):
            rel_parts = f.relative_to(site_dir).parts
            if f.is_file() and not set(rel_parts) & set(paths.SITE_IGNORED_DIRS):
                site_hashes["/".join(rel_parts)] = io.sha256_file(f)

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
    trace.append(proj_dir, "step", script="handoff")
    guided_lines = finish_guided(proj_dir, brief) + finish_deep(proj_dir, brief, report_summary)
    explain.write(proj_dir)

    lines = [
        f"Serah terima selesai untuk proyek '{slug}':",
        "  - HANDOFF.md berhasil dibuat",
        "  - API_CONTRACT.md berhasil disusun",
        "  - EXPLAIN.html berhasil dibuat (penjelasan keputusan untuk developer)",
    ]
    if no_provenance:
        lines.append("  - provenance.json dilewati (--no-provenance), generator meta tag dibersihkan")
    else:
        lines.append(f"  - provenance.json tercatat ({len(site_hashes)} file di-hash)")

    lines.extend(guided_lines)
    lines.append("")
    lines.append("=== ISI HANDOFF.MD ===")
    lines.extend(handoff_md.strip().splitlines())

    return lines, "handoff complete"


def main():
    """
    Titik masuk CLI: membaca slug dan opsi --no-provenance dari argumen lalu menjalankan handoff().

    I.S. : sys.argv berisi slug proyek dan opsi.
    F.S. : Hasil handoff() dikembalikan; argparse keluar dengan kode 2 bila argumen salah.
    """
    parser = argparse.ArgumentParser(description="Susun paket serah terima proyek.")
    parser.add_argument("slug", help="Slug proyek")
    parser.add_argument("--no-provenance", action="store_true", help="Lewati pembuatan provenance.json")

    args = parser.parse_args()
    return handoff(args.slug, no_provenance=args.no_provenance)


if __name__ == "__main__":
    report.run(main)
