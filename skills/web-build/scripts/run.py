# ============================================================
# File      : run.py
# Proyek    : web-skills
# Deskripsi : Satu pintu untuk semua skrip web-build. Memastikan paket Python
#             dan alat Node tersedia (memasangnya sekali ke cache bila perlu),
#             lalu menjalankan skrip yang diminta di proses yang sama.
#             Subperintah 'path' mencetak folder proyek.
# ============================================================

import os
import platform
import runpy
import sys
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import deps, paths, report
from lib.report import EXIT_INVALID, fail

# ============================================================
# ========================= KONSTANTA ========================
# ============================================================

SCRIPTS = (
    "validate_brief",
    "gaps",
    "serve",
    "pick_direction",
    "compile_tokens",
    "scaffold",
    "context",
    "check",
    "handoff",
)

MIN_PYTHON = (3, 11)


# ============================================================
# ======================== SUBPERINTAH =======================
# ============================================================


def project_path(args):
    """
    Mencetak folder proyek untuk satu slug tanpa membuat apa pun.

    I.S. : args berisi tepat satu slug.
    F.S. : Baris 'PROJECT: <folder absolut>' dan langkah berikutnya dikembalikan;
           ScriptExit kode 1 bila slug tidak sah.
    """
    if len(args) != 1 or not paths.is_valid_slug(args[0]):
        fail(EXIT_INVALID, "Penggunaan: run.py path <slug> (slug kebab-case huruf kecil).",
             "choose a kebab-case slug and run path again")

    folder = paths.project_dir(args[0]).resolve()

    return [f"PROJECT: {folder}"], "write the project files in that folder"


def prepare_dependencies():
    """
    Memastikan paket Python dan alat Node siap sebelum skrip dijalankan.

    I.S. : paths.REPO_ROOT berisi requirements.txt, package.json, package-lock.json.
    F.S. : Paket Python bisa diimpor, juga oleh proses anak lewat PYTHONPATH (serve.py
           menjalankan validate_brief.py sebagai proses terpisah); PD_NODE_MODULES menunjuk
           node_modules yang dipakai.
    """
    cache = deps.cache_root()
    target = deps.ensure_python_packages(paths.REPO_ROOT, cache)

    if target is not None:
        existing = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = os.pathsep.join([str(target), existing] if existing else [str(target)])

    node_modules = deps.ensure_node_tools(paths.REPO_ROOT, cache)
    os.environ["PD_NODE_MODULES"] = str(node_modules)


# ============================================================
# ======================== LOGIKA UTAMA ======================
# ============================================================


def main():
    """
    Titik masuk CLI: memeriksa Python dan perintah, lalu menjalankan path atau satu skrip.

    I.S. : sys.argv berisi perintah dan argumennya.
    F.S. : Untuk path: hasil project_path dikembalikan. Untuk skrip: dependensi disiapkan
           dan skrip dijalankan; skrip itu sendiri mencetak NEXT: dan mengakhiri proses
           dengan kode keluarnya. ScriptExit kode 1 untuk Python lama atau perintah salah.
    """
    if sys.version_info < MIN_PYTHON:
        fail(EXIT_INVALID,
             f"Python {platform.python_version()} terlalu lama; web-skills butuh Python 3.11 atau lebih baru.",
             "tell the user to install Python 3.11 or newer, then run the same command again")

    commands = ("path", *SCRIPTS)

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        given = sys.argv[1] if len(sys.argv) > 1 else "(kosong)"
        fail(EXIT_INVALID, [f"Perintah tidak dikenal: {given}", f"Perintah yang sah: {', '.join(commands)}"],
             "use one of the listed commands")

    command, args = sys.argv[1], sys.argv[2:]

    if command == "path":
        return project_path(args)

    prepare_dependencies()

    script = Path(__file__).resolve().parent / f"{command}.py"
    sys.argv = [str(script), *args]
    runpy.run_path(str(script), run_name="__main__")

    # Setiap skrip mengakhiri proses sendiri; baris ini hanya tercapai bila skrip berubah
    fail(EXIT_INVALID, f"{command}.py selesai tanpa kode keluar.", "report this to the maintainer")


if __name__ == "__main__":
    report.run(main)
