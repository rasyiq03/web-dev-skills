# ============================================================
# File      : signals.py
# Proyek    : ScaffolDev
# Deskripsi : Sinyal Agentivism (P1-P6) satu proyek, dihitung dari graf
#             konteks, trace.jsonl, dan report.json. Hanya hal yang bisa
#             diatribusikan yang dihitung; sisanya disebut terus terang.
# ============================================================

from pathlib import Path

from lib import graph, guided, io, trace

# ============================================================
# ========================= KONSTANTA ========================
# ============================================================

TEXT = {
    "id": {
        "title": "Sinyal pembelajaran (Agentivism)",
        "intro": "Angka ini menunjukkan seberapa besar peran Anda dalam keputusan, bukan seberapa bagus situsnya.",
        "p1": "P1 Tanggung jawab tetap pada Anda: {owned} dari {total} keputusan Anda buat atau terima",
        "p2": "P2 Verifikasi: {verified} langkah pemeriksaan (memilih, membandingkan, memberi alasan, menebak)",
        "p3": "P3 Mengolah ulang: {changed} keputusan Anda ubah sendiri (suntingan file tidak bisa diatribusikan, jadi tidak dihitung)",
        "p4": "P4 Hasil dan pemahaman: check {errors} error, {warnings} peringatan; uji pemahaman: {acceptance}",
        "p5": "P5 Jejak proses: {events} peristiwa tercatat di trace.jsonl",
        "p6_high": "P6 Risiko ketergantungan: tinggi. Tidak ada keputusan yang Anda periksa sendiri. Coba mode terpandu, atau terima keputusan dengan alasan Anda (decide --accept).",
        "p6_low": "P6 Risiko ketergantungan: rendah. Anda memeriksa setidaknya satu keputusan sendiri.",
        "p6_deep": "P6 Risiko ketergantungan: tinggi, dan itu wajar di mode deep work karena dewan AI yang memutuskan. Agar tetap paham, buka EXPLAIN.html, jawab dua soal uji pemahamannya, dan terima keputusan yang penting dengan alasan Anda (decide --accept).",
        "not_asked": "tidak ditanyakan (bukan mode terpandu)",
    },
    "en": {
        "title": "Learning signals (Agentivism)",
        "intro": "These numbers show how much you took part in the decisions, not how good the site is.",
        "p1": "P1 Responsibility stays with you: you made or accepted {owned} of {total} decisions",
        "p2": "P2 Verification: {verified} checking moves (pick, compare, justify, predict)",
        "p3": "P3 Reworking: you changed {changed} decisions yourself (file edits cannot be attributed, so they are not counted)",
        "p4": "P4 Result and understanding: check {errors} errors, {warnings} warnings; understanding check: {acceptance}",
        "p5": "P5 Process trace: {events} events recorded in trace.jsonl",
        "p6_high": "P6 Dependence risk: high. You checked none of the decisions yourself. Try guided mode, or accept decisions with your own reason (decide --accept).",
        "p6_low": "P6 Dependence risk: low. You checked at least one decision yourself.",
        "p6_deep": "P6 Dependence risk: high, which is expected in deep work mode because the AI council decided. To stay in the loop, open EXPLAIN.html, answer its two questions, and accept the decisions that matter with your own reason (decide --accept).",
        "not_asked": "not asked (not guided mode)",
    },
}


# ============================================================
# ========================== HITUNG ==========================
# ============================================================


def compute(proj_dir):
    """
    Menghitung sinyal Agentivism satu proyek.

    I.S. : proj_dir berisi minimal brief.yaml; file lain boleh belum ada.
    F.S. : dict sinyal dikembalikan; tidak ada file yang ditulis.
    """
    proj_dir = Path(proj_dir)
    brief = io.read_yaml(proj_dir / "brief.yaml") or {}
    context_graph = graph.build(proj_dir)
    events = trace.read(proj_dir)
    report_path = proj_dir / "report.json"
    summary = io.read_json(report_path).get("summary", {}) if report_path.is_file() else {}

    decisions = [n for n in context_graph["nodes"] if n["type"] == "decision"]
    owned = [d for d in decisions if d["owner"] == "developer" or d.get("accepted_by") == "developer"]
    by_developer = [e for e in events if e.get("event") in ("accept", "decide") and e.get("by") == "developer"]
    verified = [e for e in by_developer if e.get("verification") not in (None, "none")]

    # Memilih satu dari lima arah dengan --pick juga langkah verifikasi (pick), dihitung sekali
    picked = 1 if any(d.get("source") == "client-picked" for d in decisions) else 0
    changed = [e for e in by_developer if e["event"] == "decide"]
    checkpoints = guided.results_from_trace(events)
    passed = [name for name, result in checkpoints.items() if result == "passed"]
    council_events = [e for e in events if e.get("event") == "council"]

    return {
        "mode": brief.get("mode", "auto"),
        "decisions": len(decisions),
        "p1_owned": len(owned),
        "p1_share": round(len(owned) / len(decisions), 2) if decisions else 0.0,
        "p2_verifications": len(verified) + picked,
        "p3_changed": len(changed),
        "p4_errors": summary.get("errors"),
        "p4_warnings": summary.get("warnings"),
        "p4_tfs": summary.get("tfs_auto"),
        "p4_acceptance": checkpoints.get("acceptance"),
        "p5_events": len(events),
        "p6_risk": "high" if not verified and not picked and not passed else "low",
        "checkpoints_passed": len(passed),
        "council_sittings": len({e["sitting"] for e in council_events}),
        "council_votes": sum(1 for e in council_events if e.get("method") == "vote"),
        "council_simulated": any(e.get("simulated") for e in council_events),
        "council_dissent": sum(e.get("dissent", 0) for e in council_events),
        "council_vetoes": sum(e.get("vetoes", 0) for e in council_events),
        "placeholders": sum(1 for n in context_graph["nodes"] if n["type"] == "placeholder"),
    }


def lines(found, lang):
    """
    Menulis sinyal sebagai daftar kalimat sederhana untuk HANDOFF.md.

    I.S. : found adalah hasil compute(); lang adalah 'id' atau 'en'.
    F.S. : (judul, pengantar, daftar kalimat) dikembalikan.
    """
    text = TEXT.get(lang, TEXT["en"])
    acceptance = found["p4_acceptance"]

    if found["mode"] != "guided":
        acceptance = text["not_asked"]
    else:
        acceptance = guided.RESULT_NAMES["id" if lang == "id" else "en"][acceptance]

    items = [
        text["p1"].format(owned=found["p1_owned"], total=found["decisions"]),
        text["p2"].format(verified=found["p2_verifications"]),
        text["p3"].format(changed=found["p3_changed"]),
        text["p4"].format(errors=found["p4_errors"] if found["p4_errors"] is not None else "-",
                          warnings=found["p4_warnings"] if found["p4_warnings"] is not None else "-",
                          acceptance=acceptance),
        text["p5"].format(events=found["p5_events"]),
        text["p6_low"] if found["p6_risk"] == "low" else text["p6_deep" if found["mode"] == "deep" else "p6_high"],
    ]

    return text["title"], text["intro"], items
