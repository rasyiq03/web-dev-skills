# ============================================================
# File      : context.py
# Proyek    : web-skills
# Deskripsi : Mencetak konteks terkompresi (linearized triples)
#             yang dibutuhkan agen untuk membangun satu halaman.
# ============================================================

import sys
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import io, paths, project, report
from lib.report import EXIT_INVALID, fail


def get_page_context(slug, page):
    """
    Menghasilkan ringkasan konteks satu halaman proyek.

    I.S. : Proyek memiliki brief, decisions, gaps, dan tipe situs.
    F.S. : Mengembalikan baris-baris konteks dan baris NEXT.
    """
    proj_dir = project.open_project(
        slug, need=["brief.yaml", "decisions.yaml", "gaps.json"]
    )
    brief = io.read_yaml(proj_dir / "brief.yaml")
    decisions = io.read_yaml(proj_dir / "decisions.yaml")
    gaps = io.read_json(proj_dir / "gaps.json")

    site_type_id = brief.get("site_type")
    site_type = project.load_site_type(site_type_id)

    # Validasi page
    all_pages = project.site_pages(brief, site_type)
    if page not in all_pages:
        fail(
            EXIT_INVALID,
            f"Halaman {page!r} tidak ditemukan pada tipe situs {site_type_id!r} (halaman yang ada: {', '.join(all_pages)}).",
            f"choose one of: {', '.join(all_pages)}",
        )

    page_file_rel = paths.page_file(page)
    first_lang = project.first_language(brief)

    # Section pada halaman ini
    page_sections = [
        s for s in site_type.get("sections", []) if s.get("page") == page
    ]
    sec_ids = [s["id"] for s in page_sections]

    # Ambil arah dan gaya
    dir_id = decisions.get("direction")
    style_dec = next(
        (d for d in decisions.get("decisions", []) if d.get("axis") == "style"),
        {},
    )
    style_id = style_dec.get("choice", "")
    style_data = project.load_style(style_id) or {}

    patterns_all = project.load_patterns()

    # Petakan layout per section dari decisions.yaml
    layout_dec = next(
        (
            d
            for d in decisions.get("decisions", [])
            if d.get("axis") == "layout"
        ),
        {},
    )
    layout_map = {}
    for pair in layout_dec.get("choice", "").split(","):
        if "=" in pair:
            k, v = pair.strip().split("=", 1)
            layout_map[k.strip()] = v.strip()

    lines = [
        f"page | {page_file_rel} | sections: {', '.join(sec_ids)}",
    ]

    # Keputusan desain
    for d in decisions.get("decisions", []):
        axis = d.get("axis")
        if axis == "layout":
            continue
        choice = d.get("choice")
        rationale = d.get("rationale")
        lines.append(f"{d['id']} | {axis} | {choice} | why: {rationale}")

    # Detail section dan polanya
    for s in page_sections:
        s_id = s["id"]
        p_kind = s.get("pattern_kind", "")
        pat_id = layout_map.get(s_id, "")
        kind_patterns = patterns_all.get(p_kind, {})
        pat_desc = (
            kind_patterns.get(pat_id, {}).get("layout", "")
            if pat_id
            else s.get("purpose", "")
        )
        lines.append(f"section | {s_id} | pattern {pat_id} | layout: {pat_desc}")

    # Token-token penting
    tokens_file = proj_dir / "tokens.json"
    if tokens_file.is_file():
        tokens_data = io.read_json(tokens_file)
        var_names = []
        for grp in ["color", "font", "size", "space", "border", "shadow", "motion"]:
            for name in tokens_data.get(grp, {}).keys():
                var_names.append(f"--pd-{grp}-{name}")
        lines.append(f"tokens | {' '.join(var_names)}")

    # Komponen & signature moves dari gaya
    for comp_name, comp_desc in style_data.get("components", {}).items():
        lines.append(f"component | {comp_name} | {comp_desc}")

    for move in style_data.get("signature_moves", []):
        lines.append(f"signature | {move}")

    # Placeholders
    placeholders = gaps.get("placeholders", {})
    ph_list = list(placeholders.values())
    if ph_list:
        lines.append(f"placeholders | {' '.join(ph_list)}")

    # Konten file
    lines.append(f"content | content/{first_lang}.yaml#{page}")

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
