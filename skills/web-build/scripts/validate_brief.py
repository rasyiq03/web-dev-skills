# ============================================================
# File      : validate_brief.py
# Proyek    : web-skills
# Deskripsi : Memvalidasi brief.yaml terhadap skema, kecocokan slug,
#             dan ketersediaan field wajib dari tipe situs.
# ============================================================

import sys
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import io, project, report
from lib.report import EXIT_ASK, EXIT_INVALID, fail


# ============================================================
# ========================== VALIDASI ========================
# ============================================================


def validate(slug):
    """
    Menjalankan seluruh pemeriksaan pada projects/<slug>/brief.yaml.

    I.S. : Folder proyek ada; file brief.yaml mungkin belum lengkap atau tidak valid.
    F.S. : Mengembalikan baris ringkasan dan 'run gaps.py', atau keluar dengan kode:
           1 bila skema salah atau slug tidak cocok;
           3 bila ada field wajib tipe situs yang unknown.
    """
    proj_dir = project.open_project(slug, need=["brief.yaml"])
    brief_path = proj_dir / "brief.yaml"
    brief = io.read_yaml(brief_path)

    if not isinstance(brief, dict):
        fail(EXIT_INVALID, "brief.yaml harus berupa objek pemetaan YAML.",
             "format brief.yaml as a YAML mapping")

    # 1. Validasi skema
    errors = project.schema_errors(brief, "brief.schema.json")
    if errors:
        lines = ["Galat skema pada brief.yaml:"] + [f"  - {err}" for err in errors]
        fail(EXIT_INVALID, lines, "fix brief.yaml following schemas/brief.schema.json")

    # 2. Kecocokan slug dengan nama folder
    brief_slug = brief.get("slug")
    if brief_slug != slug:
        fail(
            EXIT_INVALID,
            f"Slug di brief.yaml ({brief_slug!r}) tidak cocok dengan folder ({slug!r}).",
            f"set slug to '{slug}' in brief.yaml",
        )

    # 3. Pemeriksaan tipe situs dan required_fields
    site_type_id = brief.get("site_type")
    site_type = project.load_site_type(site_type_id)
    lang = project.first_language(brief)

    required_fields = site_type.get("required_fields", [])
    unknown_required = [f for f in required_fields if project.is_unknown(brief, f)]

    if unknown_required:
        questions_map = {}
        for q in site_type.get("questions", []):
            field_name = q.get("field")
            ask = q.get("ask", {})
            question_text = ask.get(lang) or ask.get("id") or ask.get("en")
            if field_name and question_text:
                questions_map[field_name] = question_text

        prompt_lines = ["Field wajib belum diisi; mohon tanyakan kepada pengguna:"]
        for f in unknown_required:
            q_text = questions_map.get(f, f"Mohon isi: {f}")
            prompt_lines.append(f"  - [{f}] {q_text}")

        fail(EXIT_ASK, prompt_lines, "answer the questions and update brief.yaml")

    # Sukses
    reqs = project.requirements(brief)
    io.save_state(proj_dir, step="brief", slug=slug)

    summary_lines = [
        f"Brief sah untuk proyek '{slug}' (tipe: {site_type_id}, bahasa: {', '.join(brief.get('languages', []))}).",
        f"{len(reqs)} requirement ditemukan:",
    ]
    for r in reqs:
        val_str = str(r['value'])
        if len(val_str) > 50:
            val_str = val_str[:47] + "..."
        summary_lines.append(f"  - {r['id']}: {val_str} ({r['source']})")

    return summary_lines, "run gaps.py"


def main():
    if len(sys.argv) < 2:
        fail(EXIT_INVALID, "Penggunaan: python validate_brief.py <slug>", "specify a project slug")
    return validate(sys.argv[1])


if __name__ == "__main__":
    report.run(main)
