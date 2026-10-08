# ============================================================
# File      : node_tools.py
# Deskripsi : Menjalankan alat Node (Prettier, ESLint, stylelint, html-validate)
#             langsung dari node_modules milik repo, sehingga versi yang dipin
#             selalu dipakai dan proyek boleh berada di luar repo.
# ============================================================

import re
import subprocess

from lib import io, paths

# Kode keluar buatan saat alat atau node tidak bisa dijalankan sama sekali
EXIT_NOT_RUN = 127

ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


# ============================================================
# ======================= MENJALANKAN ========================
# ============================================================


def tool_command(package):
    """
    Menyusun perintah untuk menjalankan bin satu paket Node milik repo.

    I.S. : package adalah nama paket di node_modules repo, misalnya eslint.
    F.S. : List ['node', <path bin absolut>] dikembalikan, atau None bila paket tidak terpasang.
    """
    pkg_dir = paths.NODE_MODULES / package
    manifest = pkg_dir / "package.json"

    if not manifest.is_file():
        return None

    bin_field = io.read_json(manifest).get("bin")

    if isinstance(bin_field, dict):
        bin_field = bin_field.get(package)

    if not bin_field:
        return None

    return ["node", str((pkg_dir / bin_field).resolve())]


def run_tool(package, args, cwd):
    """
    Menjalankan satu alat Node dari node_modules repo tanpa npx dan tanpa shell.

    I.S. : cwd adalah folder proyek; args adalah argumen CLI alat (glob relatif ke cwd).
    F.S. : CompletedProcess dikembalikan. Bila paket atau node tidak ditemukan, returncode
           bernilai EXIT_NOT_RUN dan stderr berisi alasannya.
    """
    command = tool_command(package)

    if command is None:
        reason = f"Paket {package} tidak ditemukan di {paths.NODE_MODULES}."
        return subprocess.CompletedProcess(args, EXIT_NOT_RUN, "", reason)

    try:
        return subprocess.run(
            command + list(args),
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(args, EXIT_NOT_RUN, "", "Perintah node tidak ditemukan di PATH.")


# ============================================================
# ======================== KEGAGALAN =========================
# ============================================================


def failure_detail(result):
    """
    Meringkas pesan galat alat menjadi satu baris pendek.

    I.S. : result adalah CompletedProcess dari run_tool.
    F.S. : Tiga baris pertama stderr (atau stdout) yang bukan stack trace dikembalikan,
           digabung dengan ' | ' dan dipotong hingga 400 karakter.
    """
    text = ANSI_PATTERN.sub("", result.stderr or result.stdout or "")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and not ln.startswith("at ")]

    return " | ".join(lines[:3])[:400] or "tanpa pesan"


def failure_finding(package, result, target):
    """
    Mengubah alat yang gagal berjalan menjadi satu temuan error, agar tidak pernah lolos diam-diam.

    I.S. : result adalah CompletedProcess alat yang gagal; target adalah glob yang diperiksa.
    F.S. : Dict temuan dengan rule 'tool-failed' dan category 'lint' dikembalikan.
    """
    return {
        "rule": "tool-failed",
        "category": "lint",
        "level": "error",
        "file": target,
        "line": 1,
        "message": f"{package} gagal berjalan (kode keluar {result.returncode}): {failure_detail(result)}",
        "fix": "Bila pesan menyebut file di site/, perbaiki sintaks file itu. Bila menyebut paket, "
        "modul, atau node yang tidak ditemukan, jalankan npm run setup di root repo.",
    }
