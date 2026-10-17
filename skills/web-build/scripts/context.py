# ============================================================
# File      : context.py
# Proyek    : ScaffolDev
# Deskripsi : Mencetak konteks terkompresi (linearized triples)
#             yang dibutuhkan agen untuk membangun satu halaman,
#             diambil dari graf konteks (graph.json).
# ============================================================

import sys
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import graph, io, paths, project, report
from lib.report import EXIT_INVALID, fail


def get_page_context(slug, page):
    """
    Menghasilkan ringkasan konteks satu halaman proyek dari graf konteks.

    I.S. : Proyek memiliki brief, decisions, gaps, dan tipe situs.
    F.S. : graph.json diperbarui; baris-baris konteks dan baris NEXT dikembalikan.
    """
    proj_dir = project.open_project(
        slug, need=["brief.yaml", "decisions.yaml", "gaps.json"]
    )
    brief = io.read_yaml(proj_dir / "brief.yaml")
    context_graph = graph.refresh(proj_dir)
    pages = [node["id"].split(":", 1)[1] for node in context_graph["nodes"] if node["type"] == "page"]

    # Validasi page
    if page not in pages:
        fail(
            EXIT_INVALID,
            f"Halaman {page!r} tidak ditemukan pada tipe situs {brief.get('site_type')!r} (halaman yang ada: {', '.join(pages)}).",
            f"choose one of: {', '.join(pages)}",
        )

    view = graph.page_view(context_graph, page)
    page_file_rel = paths.page_file(page)

    lines = [
        f"page | {page_file_rel} | sections: {', '.join(n['label'] for n in view['sections'])}",
    ]

    # Keputusan desain; layout sudah tampil per seksi
    for d in view["decisions"]:
        if d.get("axis") == "layout":
            continue
        lines.append(f"{d['id']} | {d.get('axis')} | {d.get('choice')} | why: {d.get('why')}")

    # Detail section dan polanya
    for s in view["sections"]:
        lines.append(f"section | {s['label']} | pattern {s.get('pattern', '')} | layout: {s.get('layout', '')}")

    # Token-token penting
    if view["tokens"]:
        lines.append(f"tokens | {' '.join(n['label'] for n in view['tokens'])}")

    # Komponen & signature moves dari gaya
    for comp_name, comp_desc in view["style"].get("components", {}).items():
        lines.append(f"component | {comp_name} | {comp_desc}")

    for move in view["style"].get("signature", []):
        lines.append(f"signature | {move}")

    # Placeholders
    if view["placeholders"]:
        lines.append(f"placeholders | {' '.join(n['label'] for n in view['placeholders'])}")

    # Konten file
    lines.append(f"content | content/{project.first_language(brief)}.yaml#{page}")

    # Hitung perkiraan token (characters / 4)
    total_chars = sum(len(line) + 1 for line in lines)
    approx_tokens = round(total_chars / 4)
    lines.append(f"approx_tokens | ~{approx_tokens} tokens (target: < 1500)")

    return lines, f"build {page_file_rel} (see skills/web-build/SKILL.md step 6)"


def main():
    """
    Titik masuk CLI: membaca slug dan halaman dari argumen lalu menjalankan get_page_context().

    I.S. : sys.argv berisi slug dan id halaman, atau kurang dari itu.
    F.S. : Hasil get_page_context() dikembalikan; keluar dengan kode 1 bila argumen kurang.
    """
    if len(sys.argv) < 3:
        fail(
            EXIT_INVALID,
            "Penggunaan: python context.py <slug> <page>",
            "specify slug and page (e.g. kopi-senja index)",
        )
    return get_page_context(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    report.run(main)
