# ============================================================
# File      : explain.py
# Proyek    : ScaffolDev
# Deskripsi : Menulis EXPLAIN.html, halaman penjelasan proyek untuk
#             developer: langkah dan pelakunya, kartu keputusan, graf
#             konteks yang bisa diklik, isian kosong, dan uji pemahaman.
# ============================================================

import sys
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import explain, project, report
from lib.report import EXIT_INVALID, fail


def main():
    """
    Titik masuk CLI: menulis EXPLAIN.html untuk satu proyek.

    I.S. : sys.argv berisi slug proyek yang punya brief.yaml.
    F.S. : EXPLAIN.html dan graph.json diperbarui; ringkasan dan NEXT dikembalikan.
    """
    if len(sys.argv) < 2:
        fail(EXIT_INVALID, "Penggunaan: python explain.py <slug>", "specify the project slug")

    proj_dir = project.open_project(sys.argv[1], need=["brief.yaml"])
    path = explain.write(proj_dir)

    return [
        f"EXPLAIN.html ditulis: {path}",
        "Buka di browser; halaman ini tidak butuh internet.",
    ], "tell the user where EXPLAIN.html is and what it shows"


if __name__ == "__main__":
    report.run(main)
