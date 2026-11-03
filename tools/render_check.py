# ============================================================
# File      : render_check.py
# Proyek    : ScaffolDev
# Deskripsi : Memeriksa situs yang sudah dibangun di browser sungguhan:
#             screenshot 1440 dan 390 px, axe-core, gulir menyamping di
#             HP, dan kemiripan dengan proyek lain (warna dan tata letak).
#             Temuan ditambahkan ke report.json; sidik disimpan di
#             <work>/render.json.
# ============================================================

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RENDER_DIR = REPO_ROOT / "tools" / "render"
sys.path.insert(0, str(REPO_ROOT / "skills" / "web-build" / "scripts"))
sys.path.insert(0, str(RENDER_DIR))

import metrics  # noqa: E402
from lib import deps, io, paths, project, report  # noqa: E402
from lib.report import EXIT_CHECK_FAILED, EXIT_INVALID, fail  # noqa: E402

# Ambang awal; kalibrasi ulang dengan tools/eval (lihat IMPLEMENTATION.md §3.11)
COLOR_THRESHOLD = 12.0  # ΔE rata-rata yang dipindahkan
LAYOUT_THRESHOLD = 0.25  # bagian pohon landmark yang berbeda
SOURCE = "render_check"

AXE_LEVEL = {"critical": "error", "serious": "error", "moderate": "warning", "minor": "info"}

BROWSER_CANDIDATES = [
    "/opt/pw-browsers/chromium-*/chrome-linux/chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
]


# ============================================================
# ======================== PERSIAPAN =========================
# ============================================================


def find_browser(explicit=None):
    """
    Mencari Chromium atau Chrome yang terpasang.

    I.S. : explicit dari --browser boleh None; PD_BROWSER boleh diatur.
    F.S. : Path browser dikembalikan; ScriptExit kode 1 dengan petunjuk bila tidak ada.
    """
    for candidate in (explicit, os.environ.get("PD_BROWSER")):
        if candidate:
            if Path(candidate).is_file():
                return candidate
            fail(EXIT_INVALID, f"Browser tidak ditemukan di {candidate}.", "pass the path of Chrome or Chromium with --browser")

    for pattern in BROWSER_CANDIDATES:
        matches = sorted(Path("/").glob(pattern.lstrip("/"))) if "*" in pattern else [Path(pattern)]
        for match in matches:
            if match.is_file():
                return str(match)

    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(name)
        if found:
            return found

    fail(EXIT_INVALID, "Chrome atau Chromium tidak ditemukan.",
         "install Google Chrome, or pass its path with --browser (or set PD_BROWSER)")


def run_browser(site_dir, out_dir, browser, pages):
    """
    Menjalankan render.mjs untuk semua halaman.

    I.S. : Alat Node render terpasang di cache; browser ada.
    F.S. : Daftar hasil per halaman dikembalikan; ScriptExit kode 1 bila browser gagal.
    """
    modules = deps.ensure_node_tools(RENDER_DIR, deps.cache_root(), kind="render")
    env = {**os.environ, "NODE_PATH": str(modules)}
    script = modules.parent / "render.mjs"
    # Modul ES mencari paket dari letak skripnya, jadi skrip harus di samping node_modules
    if script.resolve() != (RENDER_DIR / "render.mjs").resolve():
        shutil.copyfile(RENDER_DIR / "render.mjs", script)

    result = subprocess.run(
        [shutil.which("node") or "node", str(script), str(site_dir), str(out_dir), browser, *pages],
        capture_output=True, text=True, encoding="utf-8", env=env, timeout=600,
    )
    if result.returncode != 0:
        fail(EXIT_INVALID, ["Pemeriksaan di browser gagal:"] + result.stderr.strip().splitlines()[-8:],
             "check that the browser path is right, then run render_check again")

    return json.loads(result.stdout)


# ============================================================
# ========================== TEMUAN ==========================
# ============================================================


def page_findings(results):
    """
    Mengubah hasil browser menjadi temuan report.json.

    I.S. : results dari render.mjs.
    F.S. : Daftar temuan dikembalikan: pelanggaran axe (lint), gulir menyamping di 390 px
           (design), dan error JavaScript di konsol (lint).
    """
    findings = []

    for page in results:
        for violation in page.get("axe", []):
            findings.append({
                "rule": f"axe-{violation['id']}", "category": "lint", "source": SOURCE,
                "level": AXE_LEVEL.get(violation.get("impact"), "warning"),
                "file": page["page"], "line": 1,
                "message": f"{violation['help']} ({violation['nodes']} elemen, mis. {violation.get('target') or '-'}).",
                "fix": f"See https://dequeuniversity.com/rules/axe/4.10/{violation['id']}.",
            })

        if page.get("scrollWidth", 390) > 390:
            findings.append({
                "rule": "horizontal-overflow", "category": "design", "source": SOURCE, "level": "error",
                "file": page["page"], "line": 1,
                "message": f"Di layar 390 px halaman selebar {page['scrollWidth']} px, jadi bergulir menyamping.",
                "fix": "Find the element wider than the screen (often a long word in a large heading or a table) and let it wrap or scroll inside itself.",
            })

        for error in sorted(set(page.get("errors", []))):
            findings.append({
                "rule": "console-error", "category": "lint", "source": SOURCE, "level": "error",
                "file": page["page"], "line": 1, "message": f"Error JavaScript: {error}",
                "fix": "Open the page with the browser console and fix the script error.",
            })

    return findings


def site_fingerprint(results):
    """
    Menggabungkan sidik semua halaman menjadi sidik situs.

    I.S. : results dari render.mjs.
    F.S. : {color: histogram semua halaman, layout: pohon landmark beranda}. Tata letak
           dibandingkan per beranda, karena jumlah halaman yang berbeda akan menenggelamkan
           perbedaan rancangan.
    """
    samples = [sample for page in results for sample in page["fingerprint"]["colors"]]
    home = next((page for page in results if page["page"] == "index.html"), results[0])
    layout = home["fingerprint"]["tree"]
    return {"color": metrics.color_histogram(samples), "layout": layout}


def homogeneity(proj_dir, fingerprint):
    """
    Membandingkan sidik situs ini dengan proyek lain di folder proyek yang sama.

    I.S. : Proyek lain boleh punya <work>/render.json dari render_check sebelumnya.
    F.S. : (perbandingan, temuan) dikembalikan; temuan warning bila jarak warna dan jarak
           tata letak ke salah satu proyek sama-sama di bawah ambang.
    """
    comparisons, findings = [], []
    here = proj_dir.parent.resolve()

    for other in sorted(here.parent.glob(f"*/{paths.WORK_DIR}/render.json")):
        if other.parent.parent.resolve() == here:
            continue
        theirs = io.read_json(other)
        color = metrics.color_distance(fingerprint["color"], [(tuple(c), w) for c, w in theirs["color"]])
        layout = metrics.layout_distance(fingerprint["layout"], theirs["layout"])
        name = other.parent.parent.name
        comparisons.append({"project": name, "color": color, "layout": layout})

        if color < COLOR_THRESHOLD and layout < LAYOUT_THRESHOLD:
            findings.append({
                "rule": "homogeneous-site", "category": "design", "source": SOURCE, "level": "warning",
                "file": "index.html", "line": 1,
                "message": f"Situs ini mirip {name}: jarak warna {color} ΔE, jarak tata letak {layout}.",
                "fix": "Pick another direction (run decide or rerun pick_direction) so clients do not get the same site.",
            })

    return comparisons, findings


def merge_report(proj_dir, findings):
    """
    Menambahkan temuan render_check ke report.json dan menghitung ulang ringkasannya.

    I.S. : report.json dari check.py boleh belum ada.
    F.S. : Temuan render_check lama diganti yang baru; summary errors/warnings/info diperbarui.
    """
    path = proj_dir / "report.json"
    data = io.read_json(path) if path.is_file() else {"summary": {}, "findings": []}
    kept = [f for f in data.get("findings", []) if f.get("source") != SOURCE]
    data["findings"] = kept + findings
    summary = data.setdefault("summary", {})
    for level, key in (("error", "errors"), ("warning", "warnings"), ("info", "info")):
        summary[key] = sum(1 for f in data["findings"] if f["level"] == level)
    io.write_json(path, data)
    return summary


# ============================================================
# ========================== UTAMA ===========================
# ============================================================


def run(slug, browser=None):
    """
    Menjalankan pemeriksaan browser untuk satu proyek.

    I.S. : Situs proyek sudah dibangun.
    F.S. : Screenshot di <work>/render/, render.json, dan report.json diperbarui; ringkasan
           dan baris NEXT dikembalikan; kode 2 bila ada error.
    """
    proj_dir = project.open_project(slug, need=["brief.yaml"])
    site_dir = paths.site_dir(proj_dir)
    pages = [p.relative_to(site_dir).as_posix() for p in paths.site_files(site_dir, "*.html")]
    if not pages:
        fail(EXIT_INVALID, f"Belum ada halaman di {site_dir}.", f"build the site first (run scaffold {slug})")

    out_dir = proj_dir / "render"
    out_dir.mkdir(exist_ok=True)
    results = run_browser(site_dir, out_dir, find_browser(browser), pages)

    fingerprint = site_fingerprint(results)
    comparisons, similar = homogeneity(proj_dir, fingerprint)
    io.write_json(proj_dir / "render.json", {**fingerprint, "comparisons": comparisons})
    findings = page_findings(results) + similar
    summary = merge_report(proj_dir, findings)

    lines = [f"Pemeriksaan browser untuk {len(pages)} halaman: {len(findings)} temuan "
             f"(report.json kini {summary['errors']} error, {summary['warnings']} peringatan)."]
    lines += [f"  - {f['level']}: {f['rule']} di {f['file']}: {f['message']}" for f in findings]
    lines += [f"  - mirip {c['project']}? warna {c['color']} ΔE, tata letak {c['layout']}" for c in comparisons]
    lines.append(f"  - Screenshot: {out_dir}")
    lines.append("Catatan: jarak tata letak dihitung dari DOM, bukan dari screenshot seperti Design "
                 "Theater (OmniParser), jadi angkanya tidak bisa dibandingkan langsung.")

    if summary["errors"]:
        fail(EXIT_CHECK_FAILED, lines, "fix the findings, run check, then render_check again")
    return lines, "run handoff.py"


def main():
    """
    Titik masuk CLI.

    I.S. : sys.argv berisi slug dan opsi --browser.
    F.S. : Hasil run() dikembalikan.
    """
    parser = argparse.ArgumentParser(description="Pemeriksaan situs di browser sungguhan.")
    parser.add_argument("slug")
    parser.add_argument("--browser", help="path Chrome atau Chromium (atau atur PD_BROWSER)")
    args = parser.parse_args()
    return run(args.slug, args.browser)


if __name__ == "__main__":
    report.run(main)
