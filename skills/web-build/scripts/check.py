# ============================================================
# File      : check.py
# Proyek    : ScaffolDev
# Deskripsi : Format kode, jalankan linter & audit, evaluasi batasan desain,
#             kelola snapshot ronde (rounds/<n>/), dan tulis report.json.
# ============================================================

import json
import shutil
import sys
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import audit_rules, io, node_tools, paths, project, report, trace
from lib.report import EXIT_CHECK_FAILED, EXIT_INVALID, fail


# ============================================================
# ====================== FORMAT & LINT =======================
# ============================================================

# Pola file situs per alat; daftar file disusun Python agar folder kerja .ScaffolDev dan
# .git tidak pernah ikut diperiksa atau diformat
PRETTIER_TARGET = ("*.html", "*.css")
JS_TARGET = ("*.js",)
CSS_TARGET = ("*.css",)
HTML_TARGET = ("*.html",)

# File sementara untuk laporan JSON stylelint (dihapus setelah dibaca)
STYLELINT_REPORT = ".stylelint-report.json"


def site_targets(site_dir, patterns, skip_vendor=False):
    """
    Menyusun daftar file situs untuk satu alat, relatif terhadap folder proyek.

    I.S. : patterns adalah pola nama file (misalnya '*.html'); skip_vendor membuang js/vendor/.
    F.S. : Daftar path POSIX relatif dikembalikan, urut, tanpa .ScaffolDev dan .git.
    """
    found = set()

    for pattern in patterns:
        for path in paths.site_files(site_dir, pattern):
            rel = path.relative_to(site_dir).as_posix()

            if not (skip_vendor and rel.startswith("js/vendor/")):
                found.add(rel)

    return sorted(found)


def run_formatters(proj_dir):
    """
    Menjalankan Prettier, ESLint, dan stylelint dengan opsi perbaikan otomatis (--fix/--write).

    I.S. : proj_dir adalah folder kerja berisi salinan konfigurasi; situs di folder induknya.
    F.S. : Kode terformat otomatis. List temuan dikembalikan: satu temuan tool-failed bila
           Prettier gagal (kegagalan ESLint dan stylelint dilaporkan oleh run_linters).
    """
    findings = []
    site_dir = paths.site_dir(proj_dir)
    pretty = site_targets(site_dir, PRETTIER_TARGET)

    if pretty:
        res_pr = node_tools.run_tool("prettier", ["--write", *prettier_config(proj_dir), *pretty], site_dir)
        if res_pr.returncode != 0:
            findings.append(node_tools.failure_finding("prettier", res_pr, "**/*.{html,css}"))

    if site_targets(site_dir, JS_TARGET, skip_vendor=True):
        node_tools.run_tool("eslint", ["--fix", "--fix-type", "layout", *eslint_args(site_dir)], site_dir)

    if site_targets(site_dir, CSS_TARGET):
        node_tools.run_tool("stylelint", ["--fix", *stylelint_args(site_dir)], site_dir)

    return findings


def prettier_config(proj_dir):
    """
    Menunjuk salinan konfigurasi Prettier di folder kerja.

    I.S. : proj_dir adalah folder kerja yang berisi .prettierrc.json.
    F.S. : Argumen --config dikembalikan (kosong bila salinannya belum ada).
    """
    config = proj_dir / ".prettierrc.json"

    return ["--config", str(config)] if config.is_file() else []


def eslint_args(site_dir):
    """
    Menyusun argumen ESLint bersama untuk mode perbaikan dan mode laporan.

    I.S. : site_dir adalah folder proyek.
    F.S. : List argumen dikembalikan. Config diambil lewat node_tools.lint_config agar impor
           plugin di eslint.config.js selalu ditemukan; salinan di proyek tetap dijaga oleh
           pemeriksaan integritas konfigurasi.
    """
    return [
        "--config",
        str(node_tools.lint_config("eslint.config.js")),
        *site_targets(site_dir, JS_TARGET, skip_vendor=True),
    ]


def stylelint_args(site_dir):
    """
    Menyusun argumen stylelint bersama untuk mode perbaikan dan mode laporan.

    I.S. : site_dir adalah folder proyek.
    F.S. : List argumen dikembalikan. Config diambil lewat node_tools.lint_config dengan
           alasan yang sama seperti ESLint (plugin stylelint-order dicari dari lokasi config).
    """
    return ["--config", str(node_tools.lint_config(".stylelintrc.json")), *site_targets(site_dir, CSS_TARGET)]


def run_json_linter(site_dir, package, args, ok_codes, target, report_file=None):
    """
    Menjalankan satu linter berformat JSON dan membaca hasilnya.

    I.S. : args sudah memuat opsi format JSON; report_file diisi bila alat menulis JSON ke
           file, bukan ke stdout.
    F.S. : (data, None) bila alat berjalan normal; (None, temuan tool-failed) bila alat
           crash, keluar dengan kode di luar ok_codes, atau keluarannya bukan JSON.
    """
    if report_file is not None:
        report_file.unlink(missing_ok=True)

    result = node_tools.run_tool(package, args, site_dir)
    raw = result.stdout

    if report_file is not None:
        raw = io.read_text(report_file) if report_file.is_file() else ""
        report_file.unlink(missing_ok=True)

    if result.returncode in ok_codes:
        try:
            return json.loads(raw), None
        except ValueError:
            pass

    return None, node_tools.failure_finding(package, result, target)


def relative_to_project(file_path, proj_dir):
    """
    Mengubah path file dari laporan linter menjadi path relatif ke folder proyek.

    I.S. : file_path adalah path absolut dari laporan linter.
    F.S. : Path POSIX relatif dikembalikan, atau file_path apa adanya bila di luar proyek.
    """
    try:
        return Path(file_path).resolve().relative_to(proj_dir.resolve()).as_posix()
    except ValueError:
        return file_path


def run_linters(proj_dir):
    """
    Menjalankan linter dengan format output JSON dan mengumpulkan findings.

    I.S. : proj_dir adalah folder kerja; situs di folder induknya.
    F.S. : List finding dengan category='lint' dikembalikan (vendor dikecualikan); path file
           relatif terhadap folder proyek. Linter yang gagal berjalan menghasilkan temuan
           tool-failed berlevel error. Alat tanpa file untuk diperiksa dilewati.
    """
    findings = []
    site_dir = paths.site_dir(proj_dir)
    es_data = st_data = hv_data = None

    # 1. ESLint JSON (kecualikan vendor); kode keluar 1 = ada pelanggaran
    failure = None
    if site_targets(site_dir, JS_TARGET, skip_vendor=True):
        es_data, failure = run_json_linter(
            site_dir, "eslint", ["-f", "json", *eslint_args(site_dir)], (0, 1), "js/**/*.js"
        )
    if failure:
        findings.append(failure)
    for file_entry in es_data or []:
        rel_file = relative_to_project(file_entry.get("filePath", ""), site_dir)
        if "vendor" in rel_file:
            continue
        for m in file_entry.get("messages", []):
            level = "error" if m.get("severity") == 2 else "warning"
            findings.append({
                "rule": m.get("ruleId") or "eslint",
                "category": "lint",
                "level": level,
                "file": rel_file,
                "line": m.get("line", 1),
                "message": m.get("message", ""),
                "fix": "Perbaiki kode JS sesuai aturan ESLint.",
            })

    # 2. stylelint JSON; stylelint 17 menulis laporan ke stderr, jadi dibaca lewat -o.
    #    Kode keluar 2 = ada pelanggaran
    failure = None
    if site_targets(site_dir, CSS_TARGET):
        st_data, failure = run_json_linter(
            site_dir,
            "stylelint",
            ["-f", "json", "-o", str(proj_dir / STYLELINT_REPORT), *stylelint_args(site_dir)],
            (0, 2),
            "css/**/*.css",
            report_file=proj_dir / STYLELINT_REPORT,
        )
    if failure:
        findings.append(failure)
    for file_entry in st_data or []:
        rel_file = relative_to_project(file_entry.get("source", ""), site_dir)
        for w in file_entry.get("warnings", []):
            level = "error" if w.get("severity") == "error" else "warning"
            findings.append({
                "rule": w.get("rule", "stylelint"),
                "category": "lint",
                "level": level,
                "file": rel_file,
                "line": w.get("line", 1),
                "message": w.get("text", ""),
                "fix": "Perbaiki gaya CSS sesuai aturan stylelint.",
            })

    # 3. html-validate JSON; kode keluar 1 = ada pelanggaran
    failure = None
    html_files = site_targets(site_dir, HTML_TARGET)
    if html_files:
        hv_data, failure = run_json_linter(
            site_dir,
            "html-validate",
            ["-f", "json", "--config", str(proj_dir / ".htmlvalidate.json"), *html_files],
            (0, 1),
            "**/*.html",
        )
    if failure:
        findings.append(failure)
    for file_entry in hv_data or []:
        rel_file = relative_to_project(file_entry.get("filePath", ""), site_dir)
        for m in file_entry.get("messages", []):
            level = "error" if m.get("severity") == 2 else "warning"
            findings.append({
                "rule": m.get("ruleId", "html-validate"),
                "category": "lint",
                "level": level,
                "file": rel_file,
                "line": m.get("line", 1),
                "message": m.get("message", ""),
                "fix": "Perbaiki struktur HTML sesuai spesifikasi.",
            })

    return findings


# ============================================================
# ========================= CHECK RUN ========================
# ============================================================

SITE_IGNORE = shutil.ignore_patterns(*paths.SITE_IGNORED_DIRS)


def run_check(slug):
    """
    Menjalankan satu ronde pemeriksaan check.py untuk proyek projects/<slug>/.

    I.S. : Proyek memiliki situs, decisions.yaml, brief.yaml, state.yaml.
    F.S. : Snapshot disimpan ke rounds/<round>/; report.json ditulis;
           bila lolos atau batas tercapai, ronde terbaik dipulihkan ke situs
           dan langkah berikutnya adalah handoff.py.
    """
    proj_dir = project.open_project(slug, need=["brief.yaml", "decisions.yaml", "state.yaml"])
    site_dir = paths.site_dir(proj_dir)
    if not paths.has_site_content(site_dir):
        fail(EXIT_INVALID, f"Situs di {site_dir} belum dibuat.", f"run scaffold.py {slug} first")

    brief = io.read_yaml(proj_dir / "brief.yaml")
    decisions = io.read_yaml(proj_dir / "decisions.yaml")
    site_type = project.load_site_type(brief.get("site_type"))
    state = io.load_state(proj_dir)

    # Kelola nomor ronde
    current_round = state.get("check_round", 0) + 1
    round_dir = proj_dir / "rounds" / str(current_round)
    round_dir.mkdir(parents=True, exist_ok=True)

    # Buat snapshot situs (tanpa .ScaffolDev dan .git) ke rounds/<round>/site SEBELUM menulis laporan
    shutil.copytree(site_dir, round_dir / "site", dirs_exist_ok=True, ignore=SITE_IGNORE)

    # 1. Format (auto-fix)
    findings = run_formatters(proj_dir)

    # 2. Lint (report)
    findings += run_linters(proj_dir)

    # 3. Integritas konfigurasi
    stored_cfg_hashes = state.get("config_hashes", {})
    for cfg_name, exp_hash in stored_cfg_hashes.items():
        cfg_path = proj_dir / cfg_name
        if not cfg_path.is_file() or io.sha256_file(cfg_path) != exp_hash:
            orig = paths.CONFIG_DIR / cfg_name
            if orig.is_file():
                shutil.copyfile(orig, cfg_path)
            findings.append({
                "rule": "config-modified",
                "category": "lint",
                "level": "error",
                "file": cfg_name,
                "line": 1,
                "message": f"Konfigurasi {cfg_name} telah diubah; isi asli dipulihkan.",
                "fix": "Jangan ubah file konfigurasi yang disalin dari config/.",
            })

    # 4. Konvensi kode (headers, banners, links, raw colors, JSDoc)
    findings += audit_rules.check_file_headers(site_dir)
    findings += audit_rules.check_html_banners_and_links(site_dir)
    findings += audit_rules.check_css_raw_color(site_dir)
    findings += audit_rules.check_js_conventions(site_dir)

    # 5. Audit Anti-Slop (Langkah 5)
    findings += audit_rules.audit_anti_slop(proj_dir, brief, decisions, site_type)

    # 6. Batasan keputusan (TFS) (Langkah 6)
    c_findings, tfs_auto = audit_rules.evaluate_constraints(proj_dir, decisions)
    findings += c_findings

    # 7. Lapisan data mock (Langkah 7)
    findings += audit_rules.check_data_layer(proj_dir, site_type)

    # 8. Paritas dwibahasa (Langkah 8)
    findings += audit_rules.check_bilingual_parity(proj_dir, brief)

    # Deduplikasi temuan
    seen_keys = set()
    unique_findings = []
    for f in findings:
        key = (f["rule"], f.get("file"), f.get("line"), f.get("message"))
        if key not in seen_keys:
            seen_keys.add(key)
            unique_findings.append(f)
    findings = unique_findings

    # 9. Signature score (Langkah 9)
    signature_score = audit_rules.compute_signature_score(site_dir, decisions, findings)

    # Ringkasan temuan
    errors_count = sum(1 for f in findings if f["level"] == "error")
    warnings_count = sum(1 for f in findings if f["level"] == "warning")
    info_count = sum(1 for f in findings if f["level"] == "info")

    lint_count = sum(1 for f in findings if f["category"] == "lint" and f["level"] in ("error", "warning"))
    design_count = sum(1 for f in findings if f["category"] == "design" and f["level"] in ("error", "warning"))

    report_data = {
        "round": current_round,
        "summary": {
            "errors": errors_count,
            "warnings": warnings_count,
            "info": info_count,
            "tfs_auto": tfs_auto,
            "signature": signature_score,
        },
        "findings": findings,
    }

    # Tulis report.json di proyek dan di folder ronde
    io.write_json(proj_dir / "report.json", report_data)
    io.write_json(round_dir / "report.json", report_data)

    # Catat riwayat ronde di state.yaml
    round_history = state.get("rounds", [])
    round_history.append({
        "round": current_round,
        "errors": errors_count,
        "warnings": warnings_count,
        "tfs_auto": tfs_auto,
    })

    # Logika penghentian ronde
    # Batas: lint maksimal ronde 5; jika hanya tersisa design findings, maksimal 2 ronde lagi.
    stop = False
    if errors_count == 0 and warnings_count == 0:
        stop = True
    elif current_round >= 5:
        stop = True
    elif lint_count == 0 and design_count > 0:
        design_only_rounds = state.get("design_only_rounds", 0) + 1
        state["design_only_rounds"] = design_only_rounds
        if design_only_rounds >= 2:
            stop = True

    io.save_state(proj_dir, check_round=current_round, rounds=round_history, last_summary=report_data["summary"])
    trace.finish(proj_dir, "check")

    lines = [
        f"Ronde {current_round} selesai:",
        f"  - Error   : {errors_count}",
        f"  - Warning : {warnings_count}",
        f"  - Info    : {info_count}",
        f"  - TFS Auto: {tfs_auto}",
        f"  - Signature: {signature_score}",
    ]

    if stop:
        # Pulihkan ronde terbaik (error paling sedikit, tie: warning paling sedikit, tie: ronde terbaru)
        best_round = min(
            round_history,
            key=lambda r: (r["errors"], r["warnings"], -r["round"]),
        )["round"]

        best_site = proj_dir / "rounds" / str(best_round) / "site"
        if best_site.is_dir():
            shutil.copytree(best_site, site_dir, dirs_exist_ok=True, ignore=SITE_IGNORE)

        lines.append(f"Pemeriksaan selesai. Ronde terbaik yang dipulihkan: Ronde {best_round}.")
        return lines, "run handoff.py"

    return lines, "fix the findings in report.json, then run check.py again"


def main():
    """
    Titik masuk CLI: membaca slug dari argumen lalu menjalankan run_check().

    I.S. : sys.argv berisi slug proyek, atau kosong.
    F.S. : Hasil run_check() dikembalikan; keluar dengan kode 1 bila slug tidak diberikan.
    """
    if len(sys.argv) < 2:
        fail(EXIT_INVALID, "Penggunaan: python check.py <slug>", "specify a project slug")
    return run_check(sys.argv[1])


if __name__ == "__main__":
    report.run(main)
