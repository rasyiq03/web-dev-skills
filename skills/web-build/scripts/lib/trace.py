# ============================================================
# File      : trace.py
# Proyek    : ScaffolDev
# Deskripsi : Jejak kerja proyek (trace.jsonl): satu baris JSON per
#             peristiwa, misalnya langkah selesai, keputusan diubah, atau
#             keputusan diterima developer. Bahan sinyal Agentivism P1-P6.
#             Tanpa jam dinding: urutan memakai nomor, tanggal dari PD_DATE.
# ============================================================

import json
from pathlib import Path

from lib import graph, io, paths

# ============================================================
# ========================= KONSTANTA ========================
# ============================================================

TRACE_FILE = "trace.jsonl"

# Langkah verifikasi yang dicatat saat developer menerima atau mengubah keputusan
VERIFICATION_MOVES = ("pick", "compare", "justify", "predict", "none")

ACTORS = ("developer", "ai", "council")


# ============================================================
# ========================== FUNGSI ==========================
# ============================================================


def read(proj_dir):
    """
    Membaca semua peristiwa di trace.jsonl.

    I.S. : trace.jsonl boleh belum ada; baris kosong diabaikan.
    F.S. : Daftar dict peristiwa dikembalikan sesuai urutan tulis.
    """
    path = Path(proj_dir) / TRACE_FILE

    if not path.is_file():
        return []

    return [json.loads(line) for line in io.read_text(path).splitlines() if line.strip()]


def append(proj_dir, event, **fields):
    """
    Menambahkan satu peristiwa ke trace.jsonl.

    I.S. : proj_dir adalah folder proyek yang ada; fields berisi nilai yang bisa jadi JSON.
    F.S. : Satu baris {seq, date, event, ...fields} ditambahkan; dict peristiwa dikembalikan.
    """
    proj_dir = Path(proj_dir)
    entry = {"seq": len(read(proj_dir)) + 1, "date": paths.today(io.load_state(proj_dir)), "event": event}
    entry.update({key: value for key, value in fields.items() if value is not None})

    with (proj_dir / TRACE_FILE).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def finish(proj_dir, script):
    """
    Menandai satu skrip pipeline selesai: mencatat peristiwa step lalu memperbarui graf.

    I.S. : Skrip sudah menulis keluarannya dan state.yaml.
    F.S. : Peristiwa step tercatat; graph.json diperbarui.
    """
    append(proj_dir, "step", script=script)
    graph.refresh(proj_dir)

