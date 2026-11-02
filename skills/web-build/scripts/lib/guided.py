# ============================================================
# File      : guided.py
# Proyek    : ScaffolDev
# Deskripsi : Mode terpandu: empat tingkat dukungan (scaffolding yang
#             memudar), tiga checkpoint verifikasi (Agentivism), profil
#             developer lintas proyek, dan aturan naik-turun tingkat.
# ============================================================

import os
from pathlib import Path

from lib import deps, graph, io

# ============================================================
# ========================= KONSTANTA ========================
# ============================================================

PROFILE_FILE = "profile.yaml"
DEFAULT_LEVEL = 2
CHECKPOINTS = ("framing", "direction", "acceptance")
RESULTS = ("passed", "failed", "skipped")

LEVEL_NAMES = {
    "id": {3: "Demonstrasi", 2: "Terbimbing", 1: "Petunjuk", 0: "Mandiri"},
    "en": {3: "Worked example", 2: "Guided", 1: "Hints", 0: "Independent"},
}

CHECKPOINT_NAMES = {
    "id": {"framing": "Membingkai masalah", "direction": "Memilih arah desain", "acceptance": "Menerima hasil"},
    "en": {"framing": "Framing the problem", "direction": "Choosing the direction", "acceptance": "Accepting the result"},
}

RESULT_NAMES = {
    "id": {"passed": "lolos", "failed": "belum lolos", "skipped": "dilewati", None: "belum"},
    "en": {"passed": "passed", "failed": "not passed", "skipped": "skipped", None: "not yet"},
}

# Langkah web-build sesudah checkpoint itu boleh dilakukan
CHECKPOINT_AFTER_STEP = {"framing": 1, "direction": 3, "acceptance": 7}

# Petunjuk untuk agen per checkpoint dan tingkat: apa yang AI lakukan, apa yang developer lakukan,
# dan kapan checkpoint dianggap lolos
INSTRUCTIONS = {
    "framing": {
        3: "Explain the brief in plain words (business, audience, goal, what success looks like) and why each fact matters for the design. Then ask: which fact matters most for the design, and why? Passed when the answer names a stated requirement.",
        2: "Show a short summary of the brief. Ask the developer to confirm or correct the audience, the goal, and what success looks like, in their own words. Passed when they confirm or correct at least the audience and the goal.",
        1: "Before showing the brief, ask the developer to state the audience, the goal, and what success looks like. Then compare with the brief together. Passed when their answer matches the brief, or they correct the brief.",
        0: "The developer writes or corrects brief.yaml themselves. Run validate_brief and report the result plainly. Passed when validate_brief passes.",
    },
    "direction": {
        3: "Show the five direction summaries. Ask the developer to predict which one fits this brief best, and why, before you reveal anything. Then run pick_direction (sampled) and explain the result against their prediction. Record decide --accept on d-style-1 with --verification predict. Passed when they made a prediction with a reason, right or wrong.",
        2: "Show the five direction cards: summary, probability, and rationale. The developer picks one and gives a reason that cites the audience, the place, the product, or the goal. Run pick_direction --pick dir-K, then decide --accept on d-style-1 with --verification pick and their reason. Passed when the reason is specific to this brief.",
        1: "Show the five cards without probabilities and without your recommendation. The developer picks and writes the reason. If the reason would fit any business, give one hint and let them try again. Run pick_direction --pick dir-K and decide --accept with --verification justify. Passed on a specific reason.",
        0: "The developer writes or edits directions.yaml, or picks a direction and changes axes with decide. You only run the scripts and report errors. Passed when pick_direction succeeds and every decide has the developer's own reason.",
    },
    "acceptance": {
        3: "Walk through EXPLAIN.html with the developer. Then ask question 1 below. Passed when the answer mentions a requirement from the reference chain.",
        2: "Ask questions 1 and 2 below before the developer opens EXPLAIN.html. Passed when both answers match the reference chains in substance.",
        1: "Ask questions 1 and 2, and let the developer build one section of their choice themselves before check runs. Passed when both answers match and check reports no errors in their section.",
        0: "The developer reads report.json and fixes the findings themselves; you only rerun check. Then ask questions 1 and 2. Passed when check has zero errors and both answers match.",
    },
}

# Cara memberi umpan balik, sesuai references/indonesia.md (santun tapi jujur)
FEEDBACK_RULE = (
    "If an answer misses, say plainly and kindly what is missing, give one hint, and allow one retry. "
    "After a second miss, record failed and explain the reference answer in plain words. Never pretend a wrong answer was right."
)


# ============================================================
# ========================== PROFIL ==========================
# ============================================================


def profile_path():
    """
    Menentukan lokasi profil developer.

    I.S. : PD_PROFILE boleh diatur.
    F.S. : Path profil dikembalikan: PD_PROFILE, atau profile.yaml di folder cache dependensi.
    """
    override = os.environ.get("PD_PROFILE")

    return Path(override) if override else deps.cache_root() / PROFILE_FILE


def load_profile():
    """
    Membaca profil developer.

    I.S. : File profil boleh belum ada.
    F.S. : dict {support_level, history} dikembalikan, dengan nilai bawaan bila belum ada.
    """
    path = profile_path()
    data = (io.read_yaml(path) or {}) if path.is_file() else {}

    return {"support_level": int(data.get("support_level", DEFAULT_LEVEL)), "history": list(data.get("history", []))}


def project_level(brief):
    """
    Menentukan tingkat dukungan untuk satu proyek.

    I.S. : brief adalah isi brief.yaml.
    F.S. : Tingkat 0..3 dikembalikan: support_level di brief, atau tingkat di profil.
    """
    if isinstance(brief.get("support_level"), int):
        return brief["support_level"]

    return load_profile()["support_level"]


def all_passed(entry):
    """
    Memeriksa apakah ketiga checkpoint satu proyek lolos.

    I.S. : entry adalah satu entri history.
    F.S. : True bila framing, direction, dan acceptance semuanya passed.
    """
    results = entry.get("checkpoints", {})

    return all(results.get(name) == "passed" for name in CHECKPOINTS)


def next_level(level, history):
    """
    Menghitung tingkat untuk proyek berikutnya (pedoman G14: paling banyak satu langkah).

    I.S. : level adalah tingkat proyek terakhir; history berurutan dari lama ke baru dan
           entri terakhir adalah proyek itu.
    F.S. : Tingkat baru dikembalikan: naik satu bila acceptance gagal; turun satu bila dua
           proyek terakhir di tingkat yang sama lolos semua; selain itu tetap.
    """
    if not history:
        return level

    if history[-1].get("checkpoints", {}).get("acceptance") == "failed":
        return min(3, level + 1)

    streak = 0

    for entry in reversed(history):
        if entry.get("level") != level or not all_passed(entry):
            break
        streak += 1

    return max(0, level - 1) if streak >= 2 else level


def record_project(project_key, level, results):
    """
    Mencatat hasil satu proyek di profil dan menghitung tingkat berikutnya.

    I.S. : project_key menandai proyek secara unik (path folder proyek).
    F.S. : Entri proyek ditulis (menggantikan entri lama untuk proyek yang sama, agar
           handoff yang diulang tidak terhitung dua kali); profil disimpan; tingkat baru
           dikembalikan.
    """
    profile = load_profile()
    history = [entry for entry in profile["history"] if entry.get("project") != project_key]
    history.append({"project": project_key, "level": level, "checkpoints": dict(results)})
    new_level = next_level(level, history)
    path = profile_path()

    path.parent.mkdir(parents=True, exist_ok=True)
    io.write_yaml(path, {"support_level": new_level, "history": history}, header="Profil developer ScaffolDev.")

    return new_level


# ============================================================
# ======================== CHECKPOINT ========================
# ============================================================


def results_from_trace(events):
    """
    Mengambil hasil terakhir tiap checkpoint dari trace.

    I.S. : events adalah hasil trace.read().
    F.S. : dict {nama checkpoint: hasil} dikembalikan; checkpoint yang belum dicatat tidak ada.
    """
    results = {}

    for entry in events:
        if entry.get("event") == "checkpoint" and entry.get("checkpoint") in CHECKPOINTS:
            results[entry["checkpoint"]] = entry.get("result")

    return results


def next_checkpoint(results):
    """
    Mencari checkpoint pertama yang belum lolos atau belum dicatat.

    I.S. : results adalah hasil results_from_trace().
    F.S. : Nama checkpoint dikembalikan, atau None bila semuanya sudah dicatat.
    """
    return next((name for name in CHECKPOINTS if name not in results), None)


def questions(context_graph):
    """
    Menyusun dua soal acceptance beserta rantai jawaban acuannya dari graf.

    I.S. : context_graph adalah hasil graph.build().
    F.S. : Daftar dict {node, kind, reference} dikembalikan; kosong bila belum ada keputusan.
    """
    nodes = context_graph["nodes"]
    decision = next((n for n in nodes if n["type"] == "decision" and n.get("axis") == "layout"), None)
    decision = decision or next((n for n in nodes if n["type"] == "decision"), None)
    found = []

    if decision:
        found.append({"node": decision, "kind": "why", "reference": graph.why(context_graph, decision["id"])})

    accent = next((n for n in nodes if n["id"] == "token:color.accent"), None)

    if accent:
        found.append({"node": accent, "kind": "impact", "reference": graph.impact(context_graph, accent["id"])})

    return found
