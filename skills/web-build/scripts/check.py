# ============================================================
# File      : check.py
# Proyek    : web-skills
# Deskripsi : Format kode, jalankan linter & audit, evaluasi batasan desain,
#             kelola snapshot ronde (rounds/<n>/), dan tulis report.json.
# ============================================================

import json
import shutil
import subprocess
import sys
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import audit_rules, io, paths, project, report
from lib.report import EXIT_CHECK_FAILED, EXIT_INVALID, fail


# ============================================================
# ====================== FORMAT & LINT =======================
# ============================================================


def run_formatters(proj_dir):
    """
    Menjalankan Prettier, ESLint, dan stylelint dengan opsi perbaikan otomatis (--fix/--write).

    I.S. : proj_dir memiliki file konfigurasi dan folder site/.
    F.S. : Kode terformat otomatis.
    """
    cmd_prettier = ["npx", "prettier", "--write", "site/**/*.{html,css}"]
    subprocess.run(cmd_prettier, cwd=proj_dir, shell=True, capture_output=True)

    cmd_eslint = [
        "npx",
        "eslint",
        "--fix",
        "--fix-type",
        "layout",
        "site/js/**/*.js",
        "--config",
        "eslint.config.js",
    ]
    subprocess.run(cmd_eslint, cwd=proj_dir, shell=True, capture_output=True)

    cmd_stylelint = ["npx", "stylelint", "--fix", "--config", ".stylelintrc.json", "site/css/**/*.css"]
    subprocess.run(cmd_stylelint, cwd=proj_dir, shell=True, capture_output=True)


def run_linters(proj_dir):
    """
    Menjalankan linter dengan format output JSON dan mengumpulkan findings.

    I.S. : proj_dir siap.
    F.S. : List finding dengan category='lint' dikembalikan.
    """
    findings = []

    # 1. ESLint JSON
    cmd_eslint = ["npx", "eslint", "-f", "json", "site/js/**/*.js", "--config", "eslint.config.js"]
    res_es = subprocess.run(cmd_eslint, cwd=proj_dir, shell=True, capture_output=True, text=True, encoding="utf-8")
    if res_es.stdout.strip():
        try:
            es_data = json.loads(res_es.stdout)
            for file_entry in es_data:
                file_path = file_entry.get("filePath", "")
                try:
                    rel_file = Path(file_path).relative_to(proj_dir).as_posix()
                except ValueError:
                    rel_file = file_path
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
        except Exception:
            pass

    # 2. stylelint JSON
    cmd_stylelint = ["npx", "stylelint", "-f", "json", "--config", ".stylelintrc.json", "site/css/**/*.css"]
    res_st = subprocess.run(cmd_stylelint, cwd=proj_dir, shell=True, capture_output=True, text=True, encoding="utf-8")
    if res_st.stdout.strip():
        try:
            st_data = json.loads(res_st.stdout)
            for file_entry in st_data:
                source = file_entry.get("source", "")
                try:
                    rel_file = Path(source).relative_to(proj_dir).as_posix()
                except ValueError:
                    rel_file = source
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
        except Exception:
            pass

    # 3. html-validate JSON
    cmd_htmlval = ["npx", "html-validate", "-f", "json", "--config", ".htmlvalidate.json", "site/**/*.html"]
    res_hv = subprocess.run(cmd_htmlval, cwd=proj_dir, shell=True, capture_output=True, text=True, encoding="utf-8")
    if res_hv.stdout.strip():
        try:
            hv_data = json.loads(res_hv.stdout)
            for file_entry in hv_data:
                file_path = file_entry.get("filePath", "")
                try:
                    rel_file = Path(file_path).relative_to(proj_dir).as_posix()
                except ValueError:
                    rel_file = file_path
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
        except Exception:
            pass

    return findings


# ============================================================
# ========================= CHECK RUN ========================
# ============================================================


def run_check(slug):
    """
    Menjalankan satu ronde pemeriksaan check.py untuk proyek projects/<slug>/.

    I.S. : Proyek memiliki site/, decisions.yaml, brief.yaml, state.yaml.
    F.S. : Snapshot disimpan ke rounds/<round>/; report.json ditulis;
           bila lolos atau batas tercapai, ronde terbaik dipulihkan ke site/
           dan langkah berikutnya adalah handoff.py.
    """
    proj_dir = project.open_project(slug, need=["brief.yaml", "decisions.yaml", "state.yaml"])
    site_dir = proj_dir / "site"
    if not site_dir.is_dir():
        fail(EXIT_INVALID, f"Folder {site_dir} belum dibuat.", f"run scaffold.py {slug} first")

    brief = io.read_yaml(proj_dir / "brief.yaml")
    decisions = io.read_yaml(proj_dir / "decisions.yaml")
    site_type = project.load_site_type(brief.get("site_type"))
    state = io.load_state(proj_dir)

    # Kelola nomor ronde
    current_round = state.get("check_round", 0) + 1
    round_dir = proj_dir / "rounds" / str(current_round)
    round_dir.mkdir(parents=True, exist_ok=True)

    # Buat snapshot site/ ke rounds/<round>/ SEBELUM menulis laporan
    shutil.copytree(site_dir, round_dir / "site", dirs_exist_ok=True)

    # 1. Format (auto-fix)
    run_formatters(proj_dir)

    # 2. Lint (report)
    findings = run_linters(proj_dir)

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

    # 5. Batasan keputusan (TFS)
    c_findings, tfs_auto = audit_rules.evaluate_constraints(proj_dir, decisions)
    findings += c_findings

    # 6. Lapisan data mock
    findings += audit_rules.check_data_layer(proj_dir, site_type)

    # Ringkasan temuan
    errors_count = sum(1 for f in findings if f["level"] == "error")
    warnings_count = sum(1 for f in findings if f["level"] == "warning")
    info_count = sum(1 for f in findings if f["level"] == "info")

    lint_count = sum(1 for f in findings if f["category"] == "lint" and f["level"] in ("error", "warning"))
    design_count = sum(1 for f in findings if f["category"] == "design" and f["level"] in ("error", "warning"))

    signature_score = 1.0 if not any(f["rule"].startswith("file-header") or f["rule"].startswith("banner") for f in findings) else 0.85

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
            shutil.copytree(best_site, site_dir, dirs_exist_ok=True)

        lines.append(f"Pemeriksaan selesai. Ronde terbaik yang dipulihkan: Ronde {best_round}.")
        return lines, "run handoff.py"

    return lines, "fix the findings in report.json, then run check.py again"


def main():
    if len(sys.argv) < 2:
        fail(EXIT_INVALID, "Penggunaan: python check.py <slug>", "specify a project slug")
    return run_check(sys.argv[1])


if __name__ == "__main__":
    report.run(main)
