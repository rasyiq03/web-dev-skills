# ============================================================
# File      : graph.py
# Proyek    : ScaffolDev
# Deskripsi : Membangun ulang graf konteks proyek (graph.json) dan
#             menjawab dua pertanyaan: apa yang terdampak bila satu
#             simpul berubah (--impact), dan kenapa simpul itu ada (--why).
# ============================================================

import argparse
import sys
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import graph, project, report
from lib.report import EXIT_INVALID, fail

# Kata kerja per jenis edge, untuk kalimat yang mudah dibaca: maju (pangkal -> ujung)
RELATION_WORDS = {
    "based_on": "berdasar pada",
    "realized_by": "diwujudkan oleh",
    "verified_by": "diperiksa oleh",
    "located_in": "ada di",
    "contains": "berisi",
    "fills": "mengisi",
    "about": "memeriksa",
    "violates": "melanggar",
}

# Kata kerja yang sama bila edge ditelusuri mundur (ujung -> pangkal)
INVERSE_WORDS = {
    "based_on": "menjadi dasar untuk",
    "realized_by": "mewujudkan",
    "verified_by": "memeriksa",
    "located_in": "berisi",
    "contains": "ada di dalam",
    "fills": "diisi oleh",
    "about": "diperiksa oleh",
    "violates": "dilanggar oleh",
}


def summary_lines(context_graph):
    """
    Meringkas isi graf: jumlah simpul per jenis dan jumlah edge.

    I.S. : context_graph adalah hasil graph.refresh().
    F.S. : Daftar baris ringkasan dikembalikan.
    """
    counts = {}

    for node in context_graph["nodes"]:
        counts[node["type"]] = counts.get(node["type"], 0) + 1

    parts = ", ".join(f"{kind} {count}" for kind, count in counts.items())

    return [
        f"Graf konteks: {len(context_graph['nodes'])} simpul ({parts}), {len(context_graph['edges'])} hubungan.",
        "Tertulis di graph.json.",
    ]


def walk_lines(context_graph, start, visits, title):
    """
    Menulis hasil telusur sebagai daftar bertingkat: tiap baris menyebut asal dan hubungannya.

    I.S. : visits adalah hasil graph.impact() atau graph.why().
    F.S. : Daftar baris dikembalikan; baris pertama menyebut simpul awal.
    """
    nodes = graph.index(context_graph)
    lines = [f"{title} {graph.describe(nodes[start])}"]

    if not visits:
        lines.append("  (tidak ada)")

    for node_id, edge_type, origin, is_forward in visits:
        words = RELATION_WORDS if is_forward else INVERSE_WORDS
        word = words.get(edge_type, edge_type)
        lines.append(f"  - {origin} {word} -> {graph.describe(nodes[node_id])}")

    return lines


def main():
    """
    Titik masuk CLI: membangun graf, lalu menjawab --impact atau --why bila diminta.

    I.S. : sys.argv berisi slug dan opsi.
    F.S. : graph.json diperbarui; ringkasan atau hasil telusur dikembalikan. ScriptExit kode 1
           bila simpul yang ditanya tidak ditemukan.
    """
    parser = argparse.ArgumentParser(description="Graf konteks proyek")
    parser.add_argument("slug")
    parser.add_argument("--impact", metavar="SIMPUL", help="apa yang terdampak bila simpul ini berubah")
    parser.add_argument("--why", metavar="SIMPUL", help="kenapa simpul ini ada")
    args = parser.parse_args()

    proj_dir = project.open_project(args.slug, need=["brief.yaml"])
    context_graph = graph.refresh(proj_dir)
    asked = args.impact or args.why

    if not asked:
        return summary_lines(context_graph), "continue with the current step; use --why or --impact to explain a node"

    start = graph.resolve(context_graph, asked)

    if start is None:
        fail(
            EXIT_INVALID,
            f"Simpul {asked!r} tidak ditemukan di graf (contoh id: d-palette-1, token:color.accent, section:index#hero).",
            "check the id in graph.json and run graph again",
        )

    if args.impact:
        return walk_lines(context_graph, start, graph.impact(context_graph, start), "Bila ini berubah:"), \
            "tell the user what changes, in plain words"

    return walk_lines(context_graph, start, graph.why(context_graph, start), "Alasan untuk"), \
        "tell the user why, in plain words"


if __name__ == "__main__":
    report.run(main)
