# ============================================================
# File      : checkpoint.py
# Proyek    : ScaffolDev
# Deskripsi : Checkpoint mode terpandu. Tanpa nama: mencetak tingkat
#             dukungan, status ketiga checkpoint, dan petunjuk untuk
#             checkpoint berikutnya. Dengan nama dan --result: mencatat
#             hasilnya di trace.jsonl.
# ============================================================

import argparse
import sys
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import graph, guided, io, project, report, trace
from lib.report import EXIT_INVALID, fail

MIN_NOTE = 10


def status_lines(brief, level, results, lang):
    """
    Menulis tingkat dukungan dan status ketiga checkpoint.

    I.S. : results adalah hasil guided.results_from_trace().
    F.S. : Daftar baris dikembalikan.
    """
    names = guided.CHECKPOINT_NAMES[lang]
    states = guided.RESULT_NAMES[lang]
    source = "brief" if isinstance(brief.get("support_level"), int) else "profil"
    lines = [f"Tingkat dukungan: {level} ({guided.LEVEL_NAMES[lang][level]}), dari {source}."]

    for name in guided.CHECKPOINTS:
        lines.append(f"  - {name} ({names[name]}): {states[results.get(name)]}")

    return lines


def question_lines(context_graph):
    """
    Menulis soal acceptance beserta rantai jawaban acuannya, untuk dinilai agen.

    I.S. : context_graph adalah hasil graph.refresh().
    F.S. : Daftar baris dikembalikan; kosong bila belum ada keputusan.
    """
    lines = []
    nodes = graph.index(context_graph)

    for number, item in enumerate(guided.questions(context_graph), start=1):
        node = item["node"]

        if item["kind"] == "why":
            lines.append(f"Question {number} (explain back): why was {node['label']} chosen for this site?")
        else:
            lines.append(f"Question {number} (predict impact): if {node['label']} (the main colour) changes, what changes with it and which checks must run again?")

        lines.append("  Reference chain:")
        lines += [f"    - {graph.describe(nodes[node_id])}" for node_id, *_ in item["reference"]]

    return lines


def show(proj_dir, brief, lang):
    """
    Mencetak status dan petunjuk checkpoint berikutnya.

    I.S. : Proyek memakai mode guided.
    F.S. : (baris, NEXT) dikembalikan.
    """
    level = guided.project_level(brief)
    results = guided.results_from_trace(trace.read(proj_dir))
    lines = status_lines(brief, level, results, lang)
    upcoming = guided.next_checkpoint(results)

    if upcoming is None:
        return lines + ["Ketiga checkpoint sudah dicatat. Handoff akan memperbarui profil developer."], \
            "continue with the current step; handoff updates the profile"

    lines += [
        "",
        f"Next checkpoint: {upcoming}, after web-build step {guided.CHECKPOINT_AFTER_STEP[upcoming]}.",
        f"At level {level}: {guided.INSTRUCTIONS[upcoming][level]}",
        f"Feedback: {guided.FEEDBACK_RULE}",
    ]

    if upcoming == "acceptance":
        lines += [""] + question_lines(graph.refresh(proj_dir))

    return lines, f"run the {upcoming} checkpoint with the developer in plain words, then record it with checkpoint --result"


def record(proj_dir, brief, name, result, note, lang):
    """
    Mencatat hasil satu checkpoint.

    I.S. : name dan result sah; note berisi ringkasan jawaban developer.
    F.S. : Peristiwa checkpoint tercatat di trace; (baris, NEXT) dikembalikan.
    """
    if len((note or "").strip()) < MIN_NOTE:
        fail(EXIT_INVALID, f"Tulis ringkasan jawaban developer di --note (minimal {MIN_NOTE} huruf).",
             "summarise what the developer said, then record again")

    level = guided.project_level(brief)
    trace.append(proj_dir, "checkpoint", checkpoint=name, result=result, level=level, note=note)
    graph.refresh(proj_dir)
    results = guided.results_from_trace(trace.read(proj_dir))
    lines = [f"Checkpoint {name} dicatat: {guided.RESULT_NAMES[lang][result]}."]
    lines += status_lines(brief, level, results, lang)
    upcoming = guided.next_checkpoint(results)

    if upcoming is None:
        return lines, "continue with the current step; handoff updates the profile"

    return lines, f"continue web-build; run checkpoint again after step {guided.CHECKPOINT_AFTER_STEP[upcoming]}"


def main():
    """
    Titik masuk CLI: menampilkan atau mencatat checkpoint mode terpandu.

    I.S. : sys.argv berisi slug, dan opsional nama checkpoint dengan --result dan --note.
    F.S. : Hasil show() atau record() dikembalikan; ScriptExit kode 1 bila proyek bukan mode guided.
    """
    parser = argparse.ArgumentParser(description="Checkpoint mode terpandu")
    parser.add_argument("slug")
    parser.add_argument("checkpoint", nargs="?", choices=guided.CHECKPOINTS)
    parser.add_argument("--result", choices=guided.RESULTS)
    parser.add_argument("--note", help="ringkasan jawaban developer")
    args = parser.parse_args()

    proj_dir = project.open_project(args.slug, need=["brief.yaml"])
    brief = io.read_yaml(proj_dir / "brief.yaml")
    lang = "id" if project.first_language(brief) == "id" else "en"

    if brief.get("mode") != "guided":
        fail(EXIT_INVALID, "Proyek ini tidak memakai mode terpandu (mode: guided di brief.yaml).",
             "set mode: guided in brief.yaml if the user wants guided mode")

    if args.checkpoint is None:
        return show(proj_dir, brief, lang)

    if args.result is None:
        fail(EXIT_INVALID, "Sebutkan hasilnya dengan --result passed, failed, atau skipped.", "add --result")

    return record(proj_dir, brief, args.checkpoint, args.result, args.note, lang)


if __name__ == "__main__":
    report.run(main)
