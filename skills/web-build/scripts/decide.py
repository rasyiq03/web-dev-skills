# ============================================================
# File      : decide.py
# Proyek    : ScaffolDev
# Deskripsi : Mengubah atau menerima satu keputusan desain (pedoman G9 dan
#             G15). Perubahan disimpan sebagai overrides di decisions.yaml,
#             lalu hanya bagian yang terdampak menurut graf yang dikerjakan
#             ulang. Setiap perubahan dan penerimaan dicatat di trace.jsonl.
# ============================================================

import argparse
import re
import shutil
import sys
from pathlib import Path

# Memungkinkan impor modul lib dan skrip saudara saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compile_tokens as tokens_script
import pick_direction
from lib import explain, graph, io, paths, project, report, trace
from lib.report import EXIT_INVALID, ScriptExit, fail

# ============================================================
# ========================= KONSTANTA ========================
# ============================================================

# Poros keputusan -> kolom arah yang diubah, dan kunci rationale-nya
AXIS_FIELD = {"palette": "palette", "typography": "type_pairing", "layout": "layout", "motion": "motion", "tone": "tone"}
RATIONALE_KEY = {"palette": "color", "typography": "typography", "layout": "layout", "motion": "motion", "tone": "tone"}

AXIS_NAMES = {"style": "gaya", "palette": "palet warna", "typography": "huruf", "layout": "tata letak", "motion": "gerak", "tone": "nada bahasa"}

MOTION_LEVELS = ("none", "low", "medium")
PRONOUNS = {"id": ("kamu", "Anda"), "en": ("you",)}

# Sama dengan batas rationale di decisions.schema.json
MIN_REASON = 10

FONT_URL = re.compile(r'href="(https://fonts\.googleapis\.com/css2[^"]+)"')


# ============================================================
# ======================== VALIDASI ==========================
# ============================================================


def parse_register(text, brief):
    """
    Membaca opsi --register seperti 'id=Anda'.

    I.S. : text boleh None.
    F.S. : dict {bahasa: kata ganti} dikembalikan; ScriptExit kode 1 bila tidak sah.
    """
    if not text:
        return {}

    lang, _, pronoun = text.partition("=")

    if lang not in brief.get("languages", []) or pronoun not in PRONOUNS.get(lang, ()):
        fail(EXIT_INVALID, f"--register {text!r} tidak sah. Contoh: id=kamu, id=Anda, en=you (bahasa harus ada di brief).",
             "use --register <lang>=<pronoun>")

    return {lang: pronoun}


def change_patch(axis, args, effective, site_type, brief):
    """
    Menerjemahkan perintah perubahan menjadi potongan overrides, sambil memeriksa nilainya.

    I.S. : axis adalah poros keputusan; effective adalah arah saat ini.
    F.S. : dict potongan overrides dikembalikan; ScriptExit kode 1 bila pilihan tidak sah.
    """
    style_data = project.load_style(effective["style"]) or {}
    choice = args.choice

    if axis == "palette":
        allowed = [p["id"] for p in style_data.get("palettes", [])]
    elif axis == "typography":
        allowed = [p["id"] for p in style_data.get("pairings", [])]
    elif axis == "motion":
        allowed = list(MOTION_LEVELS)
    elif axis == "layout":
        return layout_patch(args, site_type)
    else:
        patch = {"tone": choice}
        register = parse_register(args.register, brief)

        return {**patch, "register": register} if register else patch

    if choice not in allowed:
        fail(EXIT_INVALID, f"Pilihan {choice!r} tidak tersedia untuk {AXIS_NAMES[axis]}. Yang ada: {', '.join(allowed)}.",
             "pick one of the listed values")

    return {AXIS_FIELD[axis]: choice}


def layout_patch(args, site_type):
    """
    Memeriksa perubahan pola satu seksi.

    I.S. : args.section dan args.choice diisi pengguna.
    F.S. : {'layout': {seksi: pola}} dikembalikan; ScriptExit kode 1 bila seksi atau pola salah.
    """
    sections = {s["id"]: s for s in site_type.get("sections", [])}

    if args.section not in sections:
        fail(EXIT_INVALID, f"Untuk tata letak, sebutkan --section. Seksi yang ada: {', '.join(sections)}.",
             "add --section <section id>")

    kind = sections[args.section]["pattern_kind"]
    allowed = list(project.load_patterns().get(kind, {}))

    if args.choice not in allowed:
        fail(EXIT_INVALID, f"Pola {args.choice!r} tidak cocok untuk seksi {args.section}. Yang ada: {', '.join(allowed)}.",
             "pick one of the listed patterns")

    return {"layout": {args.section: args.choice}}


# ============================================================
# ====================== MENULIS ULANG =======================
# ============================================================


def merge_overrides(old, patch, axis, reason):
    """
    Menggabungkan potongan overrides baru dengan yang lama, beserta alasannya.

    I.S. : old adalah overrides lama (boleh kosong); reason adalah alasan pengguna.
    F.S. : dict overrides baru dikembalikan; isi dict (layout, register) digabung per kunci.
    """
    merged = {key: (dict(value) if isinstance(value, dict) else value) for key, value in (old or {}).items()}

    for key, value in patch.items():
        merged[key] = {**merged.get(key, {}), **value} if isinstance(value, dict) else value

    merged["rationale"] = {**merged.get("rationale", {}), RATIONALE_KEY[axis]: reason}

    return merged


def rebuild_decisions(slug, decisions, directions_data, site_type, overrides):
    """
    Menyusun ulang decisions.yaml dari arah terpilih plus overrides, lewat kode pick_direction.

    I.S. : overrides sudah diperiksa.
    F.S. : dict decisions baru dikembalikan; sumber poros yang diubah menjadi 'overridden',
           sumber lain tetap; ScriptExit kode 1 bila hasilnya tidak lolos skema.
    """
    new_input = {**decisions, "overrides": overrides}
    effective = project.effective_direction(new_input, directions_data)
    style_data = project.load_style(effective["style"])
    old_sources = {d["id"]: d["source"] for d in decisions.get("decisions", [])}
    changed_axes = {project.OVERRIDE_AXES[key] for key in overrides if key in project.OVERRIDE_AXES}

    data = pick_direction.build_decisions(slug, effective, "sampled", decisions.get("seed", 0), site_type, style_data)

    for dec in data["decisions"]:
        dec["source"] = "overridden" if dec["axis"] in changed_axes else old_sources.get(dec["id"], dec["source"])

    data["overrides"] = overrides
    errors = project.schema_errors(data, "decisions.schema.json")

    if errors:
        fail(EXIT_INVALID, ["Keputusan baru tidak sesuai skema:"] + errors, "report this to the maintainer")

    return data


def refresh_tokens(slug, proj_dir):
    """
    Menyusun ulang token, lalu menyalinnya ke situs dan mengganti tautan font bila berubah.

    I.S. : decisions.yaml sudah berisi overrides baru; tokens.json mungkin belum ada.
    F.S. : Daftar pekerjaan yang sudah dilakukan dikembalikan; state.step tidak mundur.
    """
    if not (proj_dir / "tokens.json").is_file():
        return []

    step = io.load_state(proj_dir).get("step")
    old_fonts = FONT_URL.findall(io.read_text(proj_dir / "fonts.html")) if (proj_dir / "fonts.html").is_file() else []
    tokens_script.compile_tokens(slug)
    io.save_state(proj_dir, step=step)
    done = ["tokens.json, tokens.css, dan fonts.html disusun ulang"]
    site_dir = paths.site_dir(proj_dir)

    if not paths.has_site_content(site_dir):
        return done

    shutil.copyfile(proj_dir / "tokens.css", site_dir / "css" / "tokens.css")
    done.append("css/tokens.css di situs diperbarui")
    new_fonts = FONT_URL.findall(io.read_text(proj_dir / "fonts.html"))

    if old_fonts and new_fonts and old_fonts != new_fonts:
        for page in paths.site_files(site_dir, "*.html"):
            text = io.read_text(page)

            if old_fonts[0] in text:
                io.write_text(page, text.replace(old_fonts[0], new_fonts[0]))

        done.append("tautan Google Fonts di setiap halaman diganti")

    return done


def retag_section(proj_dir, site_type, section_id, pattern):
    """
    Mengganti data-pd-pattern satu seksi di file halamannya.

    I.S. : Situs boleh belum di-scaffold.
    F.S. : (pekerjaan selesai, pekerjaan tersisa) dikembalikan sebagai dua daftar.
    """
    section = next(s for s in site_type["sections"] if s["id"] == section_id)
    page_file = paths.page_file(section["page"])
    path = paths.site_dir(proj_dir) / page_file

    if not path.is_file():
        return [], []

    pattern_re = re.compile(rf'(<section\b[^>]*\bid="{re.escape(section_id)}"[^>]*\bdata-pd-pattern=")[^"]*(")')
    text, count = pattern_re.subn(rf"\g<1>{pattern}\g<2>", io.read_text(path))

    if count:
        io.write_text(path, text)

    return (
        [f"data-pd-pattern seksi {section_id} di {page_file} diganti ke {pattern}"],
        [f"bangun ulang isi seksi {section_id} di {page_file} mengikuti pola {pattern}"],
    )


def downstream(slug, proj_dir, axis, patch, site_type, brief):
    """
    Mengerjakan ulang hanya bagian yang bergantung pada poros yang diubah.

    I.S. : decisions.yaml baru sudah ditulis.
    F.S. : (pekerjaan selesai, pekerjaan tersisa untuk agen) dikembalikan.
    """
    done, todo = [], []

    if axis in ("palette", "typography"):
        done += refresh_tokens(slug, proj_dir)
    elif axis == "layout":
        section_id, pattern = next(iter(patch["layout"].items()))
        done, todo = retag_section(proj_dir, site_type, section_id, pattern)
    elif axis == "tone" and (proj_dir / "content").is_dir():
        files = ", ".join(f"content/{lang}.yaml" for lang in brief.get("languages", []))
        todo.append(f"tulis ulang teks di {files} dengan nada baru, lalu perbarui halamannya")

    if paths.has_site_content(paths.site_dir(proj_dir)):
        todo.append("jalankan check lagi")

    return done, todo


# ============================================================
# ========================= KELUARAN =========================
# ============================================================


def impact_summary(context_graph, decision_id):
    """
    Meringkas dampak satu keputusan per jenis simpul, untuk dibacakan ke pengguna.

    I.S. : context_graph adalah graf sebelum perubahan.
    F.S. : Satu baris ringkasan dikembalikan.
    """
    nodes = graph.index(context_graph)
    counts = {}

    for node_id, *_ in graph.impact(context_graph, decision_id):
        kind = nodes[node_id]["type"]
        counts[kind] = counts.get(kind, 0) + 1

    parts = ", ".join(f"{count} {kind}" for kind, count in counts.items()) or "tidak ada"

    return f"Yang ikut terdampak menurut graf: {parts}."


def next_step(todo):
    """
    Menyusun baris NEXT dari pekerjaan yang tersisa.

    I.S. : todo adalah daftar pekerjaan dalam bahasa Indonesia.
    F.S. : Teks NEXT dalam bahasa Inggris dikembalikan.
    """
    if not todo:
        return "continue with the current step"

    if any(item.startswith("bangun ulang") for item in todo):
        return "rebuild the listed section with its new pattern, then run check"

    if any(item.startswith("tulis ulang") for item in todo):
        return "rewrite the copy in the new tone, update the pages, then run check"

    return "run check"


def finish(proj_dir):
    """
    Memperbarui graf, dan EXPLAIN.html bila sudah pernah dibuat.

    I.S. : trace.jsonl sudah mencatat peristiwa terbaru.
    F.S. : graph.json (dan EXPLAIN.html bila ada) mencerminkan keadaan baru.
    """
    graph.refresh(proj_dir)

    if (proj_dir / explain.EXPLAIN_FILE).is_file():
        explain.write(proj_dir)


def accept(proj_dir, decision, args):
    """
    Mencatat bahwa developer menerima satu keputusan tanpa mengubahnya.

    I.S. : decision adalah entri keputusan yang ada.
    F.S. : Peristiwa accept tercatat; graf diperbarui; ringkasan dan NEXT dikembalikan.
    """
    trace.append(proj_dir, "accept", decision=decision["id"], axis=decision["axis"], choice=decision["choice"],
                 by=args.by, verification=args.verification, reason=args.reason)
    finish(proj_dir)

    return [
        f"Keputusan {decision['id']} ({AXIS_NAMES[decision['axis']]}: {decision['choice']}) diterima oleh {args.by}.",
        f"Alasan: {args.reason} (verifikasi: {args.verification}).",
    ], "continue with the current step"


def change(slug, proj_dir, decisions, decision, args):
    """
    Mengubah satu keputusan, lalu mengerjakan ulang hanya bagian yang terdampak.

    I.S. : decision adalah entri keputusan yang ada dan bukan poros style.
    F.S. : decisions.yaml dan file turunannya diperbarui; peristiwa decide tercatat; bila
           langkah turunan gagal, decisions.yaml dikembalikan seperti semula.
    """
    axis = decision["axis"]
    brief = io.read_yaml(proj_dir / "brief.yaml")
    directions_data = io.read_yaml(proj_dir / "directions.yaml")
    site_type = project.load_site_type(brief.get("site_type"))
    effective = project.effective_direction(decisions, directions_data)

    patch = change_patch(axis, args, effective, site_type, brief)
    overrides = merge_overrides(decisions.get("overrides"), patch, axis, args.reason)
    before = graph.build(proj_dir)
    data = rebuild_decisions(slug, decisions, directions_data, site_type, overrides)
    new_decision = project.find_by_id(data["decisions"], decision["id"])
    decisions_path = proj_dir / "decisions.yaml"
    old_text = io.read_text(decisions_path)

    io.write_text(decisions_path, pick_direction.format_decisions_yaml(data))

    try:
        done, todo = downstream(slug, proj_dir, axis, patch, site_type, brief)
    except ScriptExit:
        io.write_text(decisions_path, old_text)
        raise

    trace.append(proj_dir, "decide", decision=decision["id"], axis=axis, before=decision["choice"],
                 after=new_decision["choice"], by=args.by, verification=args.verification, reason=args.reason)
    finish(proj_dir)

    lines = [
        f"Keputusan {decision['id']} ({AXIS_NAMES[axis]}) diubah: {decision['choice']} -> {new_decision['choice']}.",
        f"Alasan: {args.reason} (oleh {args.by}, verifikasi: {args.verification}).",
        impact_summary(before, decision["id"]),
    ]
    lines += [f"  - sudah: {item}" for item in done]
    lines += [f"  - masih perlu: {item}" for item in todo]

    return lines, next_step(todo)


def main():
    """
    Titik masuk CLI: mengubah (--choice) atau menerima (--accept) satu keputusan.

    I.S. : sys.argv berisi slug, id keputusan, dan opsi.
    F.S. : Hasil change() atau accept() dikembalikan; ScriptExit kode 1 bila masukan salah.
    """
    parser = argparse.ArgumentParser(description="Ubah atau terima satu keputusan desain")
    parser.add_argument("slug")
    parser.add_argument("decision", help="id keputusan, misalnya d-palette-1")
    parser.add_argument("--choice", help="nilai baru: id palet, id pasangan huruf, id pola, tingkat gerak, atau nada")
    parser.add_argument("--section", help="seksi yang polanya diganti (khusus tata letak)")
    parser.add_argument("--register", help="kata ganti baru untuk nada, misalnya id=Anda")
    parser.add_argument("--accept", action="store_true", help="terima keputusan tanpa mengubahnya")
    parser.add_argument("--reason", required=True, help="alasan dalam satu kalimat; sebut kebutuhan brief bila bisa")
    parser.add_argument("--by", choices=trace.ACTORS, default="developer")
    parser.add_argument("--verification", choices=trace.VERIFICATION_MOVES, default="justify")
    args = parser.parse_args()

    if len(args.reason.strip()) < MIN_REASON:
        fail(EXIT_INVALID, f"Alasan terlalu pendek. Tulis satu kalimat (minimal {MIN_REASON} huruf), sebaiknya menyebut kebutuhan di brief.",
             "ask the user why, in one sentence, then run decide again")

    proj_dir = project.open_project(args.slug, need=["brief.yaml", "directions.yaml", "decisions.yaml"])
    decisions = io.read_yaml(proj_dir / "decisions.yaml")
    decision = project.find_by_id(decisions.get("decisions", []), args.decision)

    if decision is None:
        ids = ", ".join(d["id"] for d in decisions.get("decisions", []))
        fail(EXIT_INVALID, f"Keputusan {args.decision!r} tidak ada. Yang ada: {ids}.", "use one of the listed decision ids")

    if args.accept:
        return accept(proj_dir, decision, args)

    if decision["axis"] == "style":
        fail(EXIT_INVALID, ["Gaya tidak bisa diganti sendirian, karena palet dan huruf bergantung padanya.",
                            "Pilih arah lain dengan pick_direction --pick dir-K, atau tulis ulang directions.yaml."],
             "ask the user which direction to pick, then run pick_direction with --pick")

    if not args.choice:
        fail(EXIT_INVALID, "Sebutkan --choice (nilai baru) atau --accept (terima tanpa mengubah).", "add --choice or --accept")

    return change(args.slug, proj_dir, decisions, decision, args)


if __name__ == "__main__":
    report.run(main)
