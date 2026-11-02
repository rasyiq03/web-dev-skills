# ============================================================
# File      : collect.py
# Proyek    : ScaffolDev
# Deskripsi : Mengumpulkan hasil semua proyek di satu folder menjadi satu
#             CSV untuk membandingkan mode auto, guided, dan deep: skor
#             check, sinyal Agentivism P1-P6, checkpoint, dan sidang dewan.
# ============================================================

import argparse
import csv
import sys
from pathlib import Path

# Impor pustaka lib dari skills/web-build/scripts
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "web-build" / "scripts"))

from lib import io, paths, report, signals
from lib.report import EXIT_INVALID, fail

# ============================================================
# ========================= KONSTANTA ========================
# ============================================================

COLUMNS = (
    "project", "mode", "site_type", "languages", "support_level", "decisions",
    "p1_owned", "p1_share", "p2_verifications", "p3_changed",
    "p4_errors", "p4_warnings", "p4_tfs", "p4_acceptance", "p5_events", "p6_risk",
    "checkpoints_passed", "council_sittings", "council_votes", "council_simulated",
    "council_dissent", "council_vetoes", "placeholders", "signature", "ready",
)

MODES = ("auto", "guided", "deep")


# ============================================================
# ========================== FUNGSI ==========================
# ============================================================


def find_projects(folders):
    """
    Mencari proyek (folder berisi .ScaffolDev/brief.yaml) di folder yang diberikan atau anaknya.

    I.S. : folders adalah daftar Path.
    F.S. : Daftar folder kerja (.ScaffolDev) dikembalikan, urut menurut path, tanpa duplikat.
    """
    found = set()

    for folder in folders:
        candidates = [folder, *(sorted(folder.iterdir()) if folder.is_dir() else [])]

        for candidate in candidates:
            work = candidate / paths.WORK_DIR

            if (work / "brief.yaml").is_file():
                found.add(work.resolve())

    return sorted(found)


def row_for(proj_dir):
    """
    Menyusun satu baris CSV untuk satu proyek.

    I.S. : proj_dir adalah folder kerja (.ScaffolDev) berisi brief.yaml.
    F.S. : dict dengan kunci COLUMNS dikembalikan.
    """
    brief = io.read_yaml(proj_dir / "brief.yaml") or {}
    found = signals.compute(proj_dir)
    report_path = proj_dir / "report.json"
    summary = io.read_json(report_path).get("summary", {}) if report_path.is_file() else {}
    ready = summary.get("errors") == 0 and summary.get("warnings") == 0

    if found["mode"] == "deep":
        ready = ready and found["council_sittings"] == 4

    row = {
        "project": f"{proj_dir.parent.parent.name}/{proj_dir.parent.name}",
        "site_type": brief.get("site_type"),
        "languages": " ".join(brief.get("languages", [])),
        "support_level": brief.get("support_level", ""),
        "signature": summary.get("signature", ""),
        "ready": ready,
    }
    row.update({key: found[key] for key in COLUMNS if key in found})

    return {key: "" if row.get(key) is None else row.get(key) for key in COLUMNS}


def mode_summary(rows):
    """
    Meringkas baris per mode untuk keluaran layar.

    I.S. : rows adalah hasil row_for() untuk semua proyek.
    F.S. : Daftar baris ringkasan dikembalikan, satu per mode yang ada.
    """
    lines = []

    for mode in MODES:
        group = [r for r in rows if r["mode"] == mode]

        if not group:
            continue

        share = sum(float(r["p1_share"] or 0) for r in group) / len(group)
        verify = sum(int(r["p2_verifications"] or 0) for r in group) / len(group)
        ready = sum(1 for r in group if r["ready"] is True)
        lines.append(f"  - {mode}: {len(group)} proyek, P1 rata-rata {share:.2f}, verifikasi rata-rata {verify:.1f}, siap pakai {ready}")

    return lines


def main():
    """
    Titik masuk CLI: membaca folder proyek dan menulis satu CSV.

    I.S. : sys.argv berisi folder (bawaan: folder proyek) dan --out.
    F.S. : CSV ditulis; ringkasan per mode dan NEXT dikembalikan. ScriptExit kode 1 bila tidak
           ada proyek.
    """
    parser = argparse.ArgumentParser(description="Kumpulkan hasil proyek ScaffolDev ke satu CSV")
    parser.add_argument("folders", nargs="*", type=Path, help="folder proyek atau folder berisi proyek")
    parser.add_argument("--out", type=Path, default=Path("eval-results.csv"))
    args = parser.parse_args()

    projects = find_projects(args.folders or [paths.projects_dir()])

    if not projects:
        fail(EXIT_INVALID, "Tidak ada proyek (folder berisi .ScaffolDev/brief.yaml) di folder yang diberikan.",
             "pass the folder that holds the projects")

    rows = [row_for(proj) for proj in projects]
    args.out.parent.mkdir(parents=True, exist_ok=True)

    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    return [f"{len(rows)} proyek ditulis ke {args.out}", *mode_summary(rows)], "open the CSV to compare the modes"


if __name__ == "__main__":
    report.run(main)
