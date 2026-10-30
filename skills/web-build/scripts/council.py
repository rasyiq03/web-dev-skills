# ============================================================
# File      : council.py
# Proyek    : ScaffolDev
# Deskripsi : Sidang dewan AI (musyawarah) di mode deep work. Tanpa
#             --record: menulis paket sidang yang sama untuk setiap peran.
#             Dengan --record: memeriksa notulen terhadap aturan
#             musyawarah, lalu menerapkan hasilnya dan mencatatnya.
# ============================================================

import argparse
import re
import sys
from pathlib import Path

# Memungkinkan impor modul lib dan skrip saudara saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pick_direction
from lib import council, explain, graph, io, paths, project, report, trace
from lib.report import EXIT_INVALID, fail

ROLE_CARDS = "skills/web-build/references/council"
EMPTY_SECTION = re.compile(r"<section\b[^>]*>\s*</section>")

NEXT_AFTER = {
    "direction": "run compile_tokens.py",
    "copy": "write the agreed copy into .ScaffolDev/content/<lang>.yaml, add the mock data, then build the first page (step 6)",
    "first-page": "apply the agreed fixes, build the remaining pages, then hold the site sitting",
    "site": "apply the agreed fixes, then run check until it reports zero errors and zero warnings",
}

# Apa yang dibahas tiap sidang, untuk kepala paket
TASKS = {
    "direction": "Choose one of the five directions in directions.yaml for this brief. Propose a direction id with reasons; critique by improving another member's case first.",
    "copy": "Agree on the copy for every section: headings, body text, and button labels, in the brief's language and the chosen tone. The Penulis drafts; the others improve it.",
    "first-page": "Review the first built page (index) against the decisions, the copy, accessibility, and the brief's facts. Agree on the fixes.",
    "site": "Review the whole site before the final check: consistency between pages, every placeholder present, nothing invented, mobile first. Agree on the fixes.",
}


# ============================================================
# =========================== PAKET ==========================
# ============================================================


def _protocol_lines(sitting):
    """
    Menulis ringkasan aturan sidang untuk kepala paket.

    I.S. : sitting adalah nama sidang yang sah.
    F.S. : Daftar baris markdown dikembalikan.
    """
    owner = council.ROLE_NAMES[council.TOPIC_OWNER[sitting]]

    return [
        "## Aturan sidang (musyawarah untuk mufakat)",
        "",
        "1. Putaran 1, usulan mandiri: setiap anggota mengusulkan tanpa melihat usulan anggota lain.",
        "2. Putaran 2, saling menanggapi: perbaiki dulu satu usulan anggota lain (target_role), baru sampaikan keberatan.",
        "3. Keberatan yang memblokir wajib menyebut bukti: id simpul graf dari daftar di bawah. Selera saja tidak bisa memblokir.",
        "4. Mufakat bila tidak ada keberatan memblokir yang belum selesai; boleh satu putaran revisi.",
        f"5. Bila tetap buntu: voting, suara {owner} dihitung dua kali. Perbedaan pendapat dicatat, tidak dibuang.",
        "6. Wakil klien boleh memveto fakta karangan; fakta itu tetap menjadi placeholder [[ISI: ...]].",
        "",
    ]


def _brief_lines(context_graph):
    """
    Menulis kebutuhan dan placeholder sebagai daftar bukti yang boleh dikutip.

    I.S. : context_graph adalah hasil graph.refresh().
    F.S. : Daftar baris markdown dikembalikan.
    """
    lines = ["## Bukti yang boleh dikutip (id simpul graf)", ""]

    for node in context_graph["nodes"]:
        if node["type"] in ("requirement", "placeholder", "decision", "check", "finding"):
            lines.append(f"- `{node['id']}`: {node['label']}" + (f" ({node['why']})" if node.get("why") else ""))

    # Token cukup satu baris; anggota mengutip id-nya, bukan nama variabel CSS
    tokens = [node["id"] for node in context_graph["nodes"] if node["type"] == "token"]
    if tokens:
        lines.append(f"- Token (kutip id-nya, misalnya `{tokens[0]}`): {', '.join(tokens)}")

    return lines + [""]


def _directions_lines(proj_dir):
    """
    Menulis kelima arah desain untuk sidang arah.

    I.S. : directions.yaml ada.
    F.S. : Daftar baris markdown dikembalikan.
    """
    data = io.read_yaml(proj_dir / "directions.yaml") or {}
    lines = ["## Lima arah desain", ""]

    for d in data.get("directions", []):
        lines.append(f"### {d['id']} ({round(d.get('probability', 0) * 100)}%): {d.get('summary', '')}")
        lines.append(f"style {d.get('style')}, palette {d.get('palette')}, type {d.get('type_pairing')}, motion {d.get('motion')}, tone {d.get('tone')}")

        for axis, text in (d.get("rationale") or {}).items():
            lines.append(f"- {axis}: {text}")

        lines.append("")

    return lines


def _material_lines(proj_dir, sitting):
    """
    Menulis bahan sidang selain arah: seksi tiap halaman dengan tujuan dan faktanya, serta
    path lengkap berkas yang perlu dibaca, supaya anggota cukup membaca paket ini.

    I.S. : brief.yaml ada; situs dan content/<lang>.yaml boleh belum ada.
    F.S. : Daftar baris markdown dikembalikan.
    """
    brief = io.read_yaml(proj_dir / "brief.yaml")
    site_type = project.load_site_type(brief.get("site_type"))
    site_dir = paths.site_dir(proj_dir)
    lang = project.first_language(brief)
    refs = paths.REPO_ROOT / "skills" / "web-build" / "references"
    lines = ["## Bahan", ""]

    for page in project.site_pages(brief, site_type):
        page_file = site_dir / paths.page_file(page)
        # Kerangka scaffold berisi seksi kosong; halaman dianggap dibangun bila tak ada lagi yang kosong
        built = " (sudah dibangun)" if page_file.is_file() and not EMPTY_SECTION.search(io.read_text(page_file)) else ""
        lines.append(f"### Halaman `{page}`: {page_file}{built}")

        for section in site_type.get("sections", []):
            if section.get("page") == page:
                facts = f" Fakta: {', '.join(section['facts'])}." if section.get("facts") else ""
                lines.append(f"- `{section['id']}`: {section.get('purpose', '')}{facts}")

        lines.append("")

    content = proj_dir / "content" / f"{lang}.yaml"
    lines.append("Baca juga:")
    lines.append(f"- Naskah: {content}" + ("" if content.is_file() else " (belum ada)"))
    lines.append(f"- Pedoman naskah: {refs / f'copy-{lang}.md'}")
    if lang == "id":
        lines.append(f"- Pedoman Indonesia: {refs / 'indonesia.md'}")
    if sitting in ("first-page", "site"):
        lines.append(f"- Laporan check: {proj_dir / 'report.json'}")
        lines.append(f"- CSS situs: {site_dir / 'css'} (tokens.css, base.css, layout.css, components.css)")

    return lines + [""]


def _report_lines(proj_dir):
    """
    Menulis ringkasan check terakhir untuk sidang tinjauan.

    I.S. : report.json boleh belum ada.
    F.S. : Daftar baris markdown dikembalikan.
    """
    path = proj_dir / "report.json"

    if not path.is_file():
        return ["## Hasil check", "", "Belum ada. Jalankan check bila halaman sudah dibangun.", ""]

    summary = io.read_json(path).get("summary", {})

    return ["## Hasil check", "", f"{summary.get('errors', 0)} error, {summary.get('warnings', 0)} peringatan.", ""]


def write_packet(proj_dir, sitting):
    """
    Menulis paket sidang: tugas, aturan, bukti, bahan sidang, dan format jawaban.

    I.S. : Proyek memakai mode deep; bahan sidang sudah ada.
    F.S. : deliberation/<sidang>.packet.md ditulis; path-nya dikembalikan.
    """
    context_graph = graph.refresh(proj_dir)
    lines = [f"# {council.SITTING_NAMES[sitting]}", "", f"Tugas: {TASKS[sitting]}", ""]
    lines += _protocol_lines(sitting) + _brief_lines(context_graph)

    if sitting == "direction":
        lines += _directions_lines(proj_dir)
    else:
        lines += _material_lines(proj_dir, sitting)
        lines += _report_lines(proj_dir)

    lines += [
        "## Format jawaban satu anggota",
        "",
        "```yaml",
        "role: <perancang|penulis|arsitek|penguji|wakil-klien>",
        "text: '<usulan atau tanggapan, satu sampai tiga kalimat; di sidang isi teks Penulis boleh menulis draf per seksi>'",
        "choice: <untuk sidang arah: dir-K>",
        "target_role: <putaran 2: anggota yang usulannya kamu perbaiki>",
        "objection: <opsional>",
        "blocking: <true bila keberatan ini harus diselesaikan dulu>",
        "evidence: [<id simpul graf>]",
        "```",
        "",
        "Apit nilai teks dengan tanda kutip tunggal (tulis '' untuk kutip di dalamnya), supaya titik dua di kalimat tidak merusak YAML.",
        "",
    ]

    path = proj_dir / council.MINUTES_DIR / f"{sitting}.packet.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    io.write_text(path, "\n".join(lines))

    return path


# ============================================================
# ========================== CATAT ===========================
# ============================================================


def record(slug, proj_dir, sitting):
    """
    Memeriksa notulen satu sidang, lalu menerapkan dan mencatat hasilnya.

    I.S. : deliberation/<sidang>.yaml ditulis pimpinan sidang.
    F.S. : Untuk sidang arah, decisions.yaml dibuat dari arah hasil sidang dengan sumber
           council; peristiwa council tercatat; graf (dan EXPLAIN.html bila ada) diperbarui.
           ScriptExit kode 1 bila notulen melanggar aturan; tidak ada yang diubah.
    """
    path = proj_dir / council.MINUTES_DIR / f"{sitting}.yaml"

    if not path.is_file():
        fail(EXIT_INVALID, f"Notulen {path.name} belum ada di {path.parent}.", "write the minutes, then record again")

    minutes = io.read_yaml(path) or {}
    directions_path = proj_dir / "directions.yaml"
    directions_data = (io.read_yaml(directions_path) or {}) if directions_path.is_file() else {}
    errors = council.validate_minutes(minutes, graph.build(proj_dir), directions_data)

    if not errors and minutes.get("sitting") != sitting:
        errors = [f"Notulen ini untuk sidang {minutes.get('sitting')!r}, bukan {sitting!r}."]

    if errors:
        fail(EXIT_INVALID, ["Notulen belum sesuai aturan musyawarah:"] + [f"  - {err}" for err in errors],
             "fix the minutes (or hold another round), then record again")

    resolution = minutes["resolution"]

    if sitting == "direction":
        pick_direction.pick(slug, pick_id=resolution["outcome"], seed_arg=0, source_override="council")

    trace.append(proj_dir, "council", sitting=sitting, method=resolution["method"], outcome=resolution["outcome"],
                 simulated=minutes["simulated"], dissent=len(resolution.get("dissent", [])),
                 vetoes=len(resolution.get("vetoes", [])))
    graph.refresh(proj_dir)

    if (proj_dir / explain.EXPLAIN_FILE).is_file():
        explain.write(proj_dir)

    how = "mufakat" if resolution["method"] == "mufakat" else "voting berbobot"
    lines = [
        f"{council.SITTING_NAMES[sitting]} dicatat: {how}, hasil {resolution['outcome']}.",
        f"Ringkasan: {resolution['summary']}",
    ]

    if minutes["simulated"]:
        lines.append("Catatan: dewan disimulasikan oleh satu agen (tanpa subagent); independensinya lebih lemah.")

    lines += [f"Beda pendapat ({d['role']}): {d['note']}" for d in resolution.get("dissent", [])]
    lines += [f"Veto wakil klien: {v['fact']} tetap {v['placeholder']}" for v in resolution.get("vetoes", [])]

    return lines, NEXT_AFTER[sitting]


def main():
    """
    Titik masuk CLI: menulis paket sidang, atau mencatat notulennya dengan --record.

    I.S. : sys.argv berisi slug, nama sidang, dan opsional --record.
    F.S. : Hasil dikembalikan; ScriptExit kode 1 bila proyek bukan mode deep.
    """
    parser = argparse.ArgumentParser(description="Sidang dewan AI mode deep work")
    parser.add_argument("slug")
    parser.add_argument("sitting", choices=council.SITTINGS)
    parser.add_argument("--record", action="store_true", help="periksa dan terapkan notulen deliberation/<sidang>.yaml")
    args = parser.parse_args()

    proj_dir = project.open_project(args.slug, need=["brief.yaml", "gaps.json"])
    brief = io.read_yaml(proj_dir / "brief.yaml")

    if brief.get("mode") != "deep":
        fail(EXIT_INVALID, "Proyek ini tidak memakai mode deep work (mode: deep di brief.yaml).",
             "set mode: deep in brief.yaml if the user wants deep work")

    if args.sitting == "direction" and not (proj_dir / "directions.yaml").is_file():
        fail(EXIT_INVALID, "Sidang arah butuh directions.yaml: tulis lima arah dulu (web-design).", "write directions.yaml first")

    if args.record:
        return record(args.slug, proj_dir, args.sitting)

    packet = write_packet(proj_dir, args.sitting)
    cards = [f"{ROLE_CARDS}/{role}.md" for role in council.MEMBERS]

    return [
        f"Paket {council.SITTING_NAMES[args.sitting]} ditulis: {packet}",
        "Kartu peran: " + ", ".join(cards),
        f"Pemilik topik (suara ganda saat voting): {council.ROLE_NAMES[council.TOPIC_OWNER[args.sitting]]}",
        f"Notulen ditulis ke: {packet.parent / (args.sitting + '.yaml')}",
    ], "hold the sitting as references/mode-deep.md says, write the minutes, then run council with --record"


if __name__ == "__main__":
    report.run(main)
