# ============================================================
# File      : gaps.py
# Proyek    : web-skills
# Deskripsi : Mengumpulkan requirement, placeholder fakta yang belum ada,
#             keputusan desain terbuka, dan pertanyaan ke gaps.json.
# ============================================================

import sys
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import io, labels, project, report
from lib.report import EXIT_INVALID, fail


# ============================================================
# ========================== GAPS ============================
# ============================================================


def build_gaps(slug):
    """
    Menghasilkan gaps.json untuk proyek projects/<slug>/.

    I.S. : projects/<slug>/brief.yaml ada dan sah.
    F.S. : File projects/<slug>/gaps.json tertulis; mencetak ringkasan jumlah
           dan baris NEXT yang sesuai (serve.py bila interaktif, directions.yaml bila tidak).
    """
    proj_dir = project.open_project(slug, need=["brief.yaml"])
    brief = io.read_yaml(proj_dir / "brief.yaml")

    site_type_id = brief.get("site_type")
    site_type = project.load_site_type(site_type_id)
    lang = project.first_language(brief)

    # 1. Requirements: semua field stated atau inferred
    reqs = project.requirements(brief)

    # 2. Placeholders: setiap fakta dari tipe situs yang belum ada atau unknown
    facts_list = site_type.get("facts", [])
    placeholders = {}
    for fact in facts_list:
        field_path = f"facts.{fact}"
        if project.is_unknown(brief, field_path):
            placeholders[fact] = labels.placeholder(fact, lang)

    # 3. Open decisions: goal, tone, style_request, brand.* yang unknown
    open_decision_fields = ["goal", "tone", "style_request"]
    brand_subfields = ["colors", "fonts", "logo"]

    open_decisions = []
    for f in open_decision_fields:
        if project.is_unknown(brief, f):
            open_decisions.append(f)

    for sf in brand_subfields:
        path = f"brand.{sf}"
        if project.is_unknown(brief, path):
            open_decisions.append(path)

    # 4. Questions: pertanyaan tipe situs yang field-nya masih unknown (maksimal 6)
    questions = []
    for q in site_type.get("questions", []):
        field_name = q.get("field")
        if field_name and project.is_unknown(brief, field_name):
            questions.append(q)
            if len(questions) >= 6:
                break

    # Tulis gaps.json
    gaps_data = {
        "slug": slug,
        "site_type": site_type_id,
        "requirements": reqs,
        "placeholders": placeholders,
        "open_decisions": open_decisions,
        "questions": questions,
    }

    gaps_file = proj_dir / "gaps.json"
    io.write_json(gaps_file, gaps_data)
    io.save_state(proj_dir, step="gaps")

    lines = [
        f"gaps.json selesai untuk '{slug}':",
        f"  - {len(reqs)} requirements",
        f"  - {len(placeholders)} placeholders",
        f"  - {len(open_decisions)} open decisions",
        f"  - {len(questions)} questions",
    ]

    is_interactive = bool(brief.get("interactive", False))
    next_step = "run serve.py" if is_interactive else "write directions.yaml (web-design skill)"

    return lines, next_step


def main():
    """
    Titik masuk CLI: membaca slug dari argumen lalu menjalankan build_gaps().

    I.S. : sys.argv berisi slug proyek, atau kosong.
    F.S. : Hasil build_gaps() dikembalikan; keluar dengan kode 1 bila slug tidak diberikan.
    """
    if len(sys.argv) < 2:
        fail(EXIT_INVALID, "Penggunaan: python gaps.py <slug>", "specify a project slug")
    return build_gaps(sys.argv[1])


if __name__ == "__main__":
    report.run(main)
