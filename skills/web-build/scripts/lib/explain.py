# ============================================================
# File      : explain.py
# Proyek    : ScaffolDev
# Deskripsi : Menyusun EXPLAIN.html: satu halaman mandiri (tanpa jaringan)
#             yang menunjukkan langkah kerja beserta pelakunya, kartu
#             keputusan, graf konteks yang bisa diklik, isian yang masih
#             kosong, dan dua soal uji pemahaman untuk developer.
# ============================================================

import html
import json
from pathlib import Path

from lib import graph, guided, io, paths, project, signals, trace

# ============================================================
# ========================= KONSTANTA ========================
# ============================================================

EXPLAIN_FILE = "EXPLAIN.html"

# Kolom graf: jenis simpul per kolom, dari masukan (kiri) sampai temuan (kanan)
COLUMNS = (("requirement", "placeholder", "minutes"), ("decision",), ("style", "token", "section"), ("check", "file"), ("finding",))
COLUMN_WIDTH = 250
NODE_WIDTH = 210
ROW_HEIGHT = 28
TOP = 44

# Poros keputusan -> kunci di directions.yaml
AXIS_FIELDS = {
    "style": "style",
    "palette": "palette",
    "typography": "type_pairing",
    "layout": "layout",
    "motion": "motion",
    "tone": "tone",
}

TEXT = {
    "id": {
        "title": "Penjelasan proyek",
        "intro": "Halaman ini menjelaskan apa yang diputuskan untuk situs ini, kenapa, dan siapa yang memutuskannya. Klik simpul di graf untuk melihat rantai alasan dan dampaknya.",
        "steps": "Langkah kerja",
        "steps_note": "Warna menunjukkan siapa yang mengerjakan langkah itu.",
        "agency": "Pembagian peran",
        "agency_note": "Dari kebutuhan dan keputusan di proyek ini:",
        "decisions": "Keputusan desain",
        "why": "Kenapa",
        "based_on": "Berdasar pada",
        "decided_by": "Diputuskan oleh",
        "alternatives": "Pilihan lain yang dipertimbangkan",
        "chosen": "dipilih",
        "impact": "Kalau diubah, ikut berubah",
        "checks": "Diperiksa oleh",
        "passed": "lolos",
        "failed": "gagal",
        "not_checked": "belum diperiksa",
        "show_in_graph": "Lihat di graf",
        "graph": "Graf konteks",
        "graph_note": "Kiri ke kanan: kebutuhan → keputusan → token dan seksi → file dan check → temuan. Klik simpul untuk menyorot rantainya; klik area kosong untuk kembali.",
        "all_pages": "Semua halaman",
        "hidden_tokens": "token lain tidak terkait keputusan dan tidak ditampilkan",
        "todo": "Yang masih harus diisi",
        "todo_note": "Fakta ini belum ada di brief, jadi situs memakai penanda [[ISI: …]]. Ganti dengan data asli sebelum situs dipakai.",
        "todo_none": "Tidak ada. Semua fakta sudah tersedia.",
        "used_in": "dipakai di",
        "not_on_site": "belum dipakai di halaman; isi bila ingin ditambahkan",
        "quality": "Hasil pemeriksaan",
        "quality_none": "Situs belum diperiksa. Jalankan langkah 7 (check).",
        "errors": "error",
        "warnings": "peringatan",
        "constraints": "aturan desain terpenuhi",
        "quiz": "Uji pemahaman",
        "quiz_note": "Coba jawab sendiri dulu, baru buka jawabannya. Menjelaskan ulang dengan kata-kata sendiri membuat pemahaman lebih awet.",
        "quiz_why": "Kenapa {axis} ini dipilih untuk situs ini?",
        "quiz_impact": "Kalau warna utama ({label}) diganti, bagian mana saja yang ikut berubah, dan aturan mana yang perlu diperiksa ulang?",
        "choice": "Pilihannya",
        "columns": ["Kebutuhan / isian / sidang", "Keputusan", "Gaya / token / seksi", "Check / file", "Temuan"],
        "answer": "Lihat jawaban",
        "owners": {"developer": "Anda", "ai": "AI", "script": "Skrip", "council": "Dewan AI"},
        "sources": {"client-picked": "dipilih klien", "sampled": "diundi skrip dari lima arah", "stated": "disebut di brief", "inferred": "ditebak AI dari brief", "overridden": "diubah setelah arah dipilih", "council": "diputuskan dewan AI lewat musyawarah"},
        "accepted": "Diterima oleh",
        "moves": {"pick": "memilih sendiri", "compare": "membandingkan pilihan", "justify": "memberi alasan", "predict": "menebak dulu sebelum melihat", "none": "tanpa pemeriksaan"},
        "not_in_directions": "tidak ada di kelima arah",
        "support": "Tingkat dukungan",
        "support_note": "Mode terpandu: bantuan AI dikurangi sedikit demi sedikit seiring Anda makin mandiri. Tiap checkpoint adalah saat Anda memeriksa dan memutuskan sendiri.",
        "next_level": "Proyek berikutnya",
        "council": "Musyawarah dewan AI",
        "council_note": "Mode deep work: lima peran AI (Perancang, Penulis, Arsitek front-end, Penguji mutu, Wakil klien) bermusyawarah di tiap titik keputusan. Notulen lengkapnya ada di folder deliberation/.",
        "sittings": {"direction": "Arah desain", "copy": "Isi teks", "first-page": "Halaman pertama", "site": "Seluruh situs"},
        "methods": {"mufakat": "mufakat", "vote": "voting berbobot"},
        "not_held": "belum diadakan",
        "simulated": "disimulasikan satu agen",
        "dissent": "beda pendapat",
        "vetoes": "veto fakta",
        "minutes": "notulen",
        "axes": {"style": "Gaya", "palette": "Palet warna", "typography": "Huruf", "layout": "Tata letak", "motion": "Gerak", "tone": "Nada bahasa"},
        "step_names": ["Brief", "Celah fakta", "Arah desain", "Token dan kerangka", "Isi teks", "Membangun halaman", "Pemeriksaan", "Serah terima"],
        "done": "selesai",
        "pending": "belum",
    },
    "en": {
        "title": "Project explanation",
        "intro": "This page explains what was decided for this site, why, and who decided it. Click a node in the graph to see its chain of reasons and what it affects.",
        "steps": "Steps",
        "steps_note": "The colour shows who did each step.",
        "agency": "Who decided",
        "agency_note": "Across the requirements and decisions in this project:",
        "decisions": "Design decisions",
        "why": "Why",
        "based_on": "Based on",
        "decided_by": "Decided by",
        "alternatives": "Other options considered",
        "chosen": "chosen",
        "impact": "Changing it affects",
        "checks": "Checked by",
        "passed": "passed",
        "failed": "failed",
        "not_checked": "not checked yet",
        "show_in_graph": "Show in graph",
        "graph": "Context graph",
        "graph_note": "Left to right: requirements → decisions → tokens and sections → files and checks → findings. Click a node to highlight its chain; click empty space to reset.",
        "all_pages": "All pages",
        "hidden_tokens": "other tokens are not tied to a decision and are hidden",
        "todo": "Still to fill in",
        "todo_note": "These facts were not in the brief, so the site shows [[ISI: …]] markers. Replace them with real data before the site goes live.",
        "todo_none": "Nothing. Every fact is available.",
        "used_in": "used in",
        "not_on_site": "not used on any page yet; fill in if you want it added",
        "quality": "Check results",
        "quality_none": "The site has not been checked yet. Run step 7 (check).",
        "errors": "errors",
        "warnings": "warnings",
        "constraints": "design rules met",
        "quiz": "Check your understanding",
        "quiz_note": "Try answering yourself before opening the answer. Explaining it in your own words makes it stick.",
        "quiz_why": "Why was this {axis} chosen for this site?",
        "quiz_impact": "If the main colour ({label}) changes, which parts change with it, and which rules need checking again?",
        "choice": "The choice",
        "columns": ["Requirements / gaps / sittings", "Decisions", "Style / tokens / sections", "Checks / files", "Findings"],
        "answer": "Show answer",
        "owners": {"developer": "You", "ai": "AI", "script": "Script", "council": "AI council"},
        "sources": {"client-picked": "picked by the client", "sampled": "drawn by the script from five directions", "stated": "stated in the brief", "inferred": "inferred by the AI", "overridden": "changed after the direction was picked", "council": "decided by the AI council"},
        "accepted": "Accepted by",
        "moves": {"pick": "picked it", "compare": "compared the options", "justify": "gave a reason", "predict": "predicted before looking", "none": "no check"},
        "not_in_directions": "not in the five directions",
        "support": "Support level",
        "support_note": "Guided mode: the AI's help shrinks step by step as you grow more independent. Each checkpoint is where you check and decide yourself.",
        "next_level": "Next project",
        "council": "AI council deliberation",
        "council_note": "Deep work mode: five AI roles (designer, copywriter, front-end architect, QA, client advocate) deliberate at each decision point. The full minutes are in the deliberation/ folder.",
        "sittings": {"direction": "Direction", "copy": "Copy", "first-page": "First page", "site": "Whole site"},
        "methods": {"mufakat": "consensus", "vote": "weighted vote"},
        "not_held": "not held yet",
        "simulated": "simulated by one agent",
        "dissent": "dissent",
        "vetoes": "fact vetoes",
        "minutes": "minutes",
        "axes": {"style": "Style", "palette": "Palette", "typography": "Type", "layout": "Layout", "motion": "Motion", "tone": "Tone"},
        "step_names": ["Brief", "Missing facts", "Direction", "Tokens and scaffold", "Copy", "Build", "Check", "Handoff"],
        "done": "done",
        "pending": "not yet",
    },
}

# Pelaku tiap langkah di mode auto, dan file yang menandai langkah itu selesai
STEP_OWNERS = ("ai", "script", None, "script", "ai", "ai", "script", "script")
STEP_MARKERS = ("brief.yaml", "gaps.json", "decisions.yaml", "site", "content", "report.json", "report.json", "HANDOFF.md")

# Telusur yang sama dengan lib/graph.py, untuk sorotan di browser
SCRIPT = """
(function () {
  var data = JSON.parse(document.getElementById('pd-graph-data').textContent);
  var svg = document.getElementById('pd-graph');
  function walk(start, fwd, back) {
    var seen = {}; seen[start] = true; var queue = [start];
    while (queue.length) {
      var cur = queue.shift();
      data.edges.forEach(function (e) {
        var next = null;
        if (e[0] === cur && fwd.indexOf(e[2]) >= 0) { next = e[1]; }
        else if (e[1] === cur && back.indexOf(e[2]) >= 0) { next = e[0]; }
        if (next !== null && !seen[next]) { seen[next] = true; queue.push(next); }
      });
    }
    return seen;
  }
  function chain(id) {
    var a = walk(id, data.impactForward, data.impactBackward);
    var b = walk(id, data.whyForward, data.whyBackward);
    Object.keys(b).forEach(function (k) { a[k] = true; });
    return a;
  }
  function show(keep) {
    svg.classList.toggle('is-focused', keep !== null);
    svg.querySelectorAll('[data-id]').forEach(function (el) {
      el.classList.toggle('is-on', keep !== null && !!keep[el.getAttribute('data-id')]);
    });
    svg.querySelectorAll('[data-edge]').forEach(function (el) {
      var ends = el.getAttribute('data-edge').split(' ');
      el.classList.toggle('is-on', keep !== null && !!keep[ends[0]] && !!keep[ends[1]]);
    });
  }
  svg.addEventListener('click', function (ev) {
    var node = ev.target.closest('[data-id]');
    show(node ? chain(node.getAttribute('data-id')) : null);
  });
  document.querySelectorAll('[data-focus]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var ids = btn.getAttribute('data-focus').split(' ').filter(Boolean);
      if (!ids.length) { show(null); return; }
      var keep = {};
      ids.forEach(function (id) { var c = chain(id); Object.keys(c).forEach(function (k) { keep[k] = true; }); });
      show(keep);
      document.getElementById('graf').scrollIntoView({ behavior: 'smooth' });
    });
  });
})();
"""

STYLE = """
:root {
  --ink: __ink__; --paper: __paper__; --accent: __accent__; --accent-ink: __accent_ink__; --muted: __muted__;
  --line: color-mix(in srgb, var(--ink) 18%, transparent);
  --soft: color-mix(in srgb, var(--ink) 6%, var(--paper));
  --own-developer: #1f6feb; --own-ai: #b45309; --own-script: #6b7280; --own-council: #7c3aed;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { --ink: __paper__; --paper: #16130f; --muted: color-mix(in srgb, __paper__ 70%, #16130f);
    --own-developer: #79b8ff; --own-ai: #f0b35a; --own-script: #a3a9b3; --own-council: #b69cff; color-scheme: dark; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink);
  font: 16px/1.6 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 1.9rem; line-height: 1.2; margin: 0 0 8px; }
h2 { font-size: 1.3rem; margin: 40px 0 8px; padding-top: 8px; border-top: 2px solid var(--ink); }
h3 { font-size: 1.05rem; margin: 0 0 8px; }
p.note { color: var(--muted); margin: 0 0 16px; }
.steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; list-style: none; padding: 0; }
.steps li { border: 1px solid var(--line); border-left: 6px solid var(--own); border-radius: 6px; padding: 8px 10px; background: var(--soft); }
.steps li.is-pending { opacity: .55; }
.steps b { display: block; } .steps small { color: var(--muted); }
.legend { display: flex; flex-wrap: wrap; gap: 12px; padding: 0; list-style: none; margin: 8px 0 0; }
.legend li::before { content: ""; display: inline-block; width: 12px; height: 12px; border-radius: 3px; background: var(--own); margin-right: 6px; vertical-align: -1px; }
.bar { display: flex; height: 14px; border-radius: 7px; overflow: hidden; border: 1px solid var(--line); }
.bar span { background: var(--own); }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
.card { border: 1px solid var(--line); border-top: 6px solid var(--own); border-radius: 8px; padding: 14px; background: var(--soft); }
.card dl { margin: 0; } .card dt { font-weight: 700; font-size: .85rem; margin-top: 10px; }
.card dd { margin: 2px 0 0; } .card ul { margin: 2px 0 0; padding-left: 18px; }
.chosen { font-weight: 700; } .ok { color: #15803d; } .bad { color: #b91c1c; }
@media (prefers-color-scheme: dark) { .ok { color: #4ade80; } .bad { color: #f87171; } }
button { font: inherit; cursor: pointer; border: 1px solid var(--ink); background: var(--paper); color: var(--ink); border-radius: 6px; padding: 4px 10px; margin-top: 10px; }
button:hover, button:focus-visible { background: var(--accent); color: var(--accent-ink); }
.filters { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; } .filters button { margin: 0; }
.graph-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; background: var(--soft); }
#pd-graph { display: block; }
#pd-graph text { fill: var(--ink); font-size: 12px; }
#pd-graph .col { font-weight: 700; fill: var(--muted); }
#pd-graph rect.box { fill: var(--paper); stroke: var(--line); }
#pd-graph rect.own { stroke: none; }
#pd-graph path { fill: none; stroke: var(--line); stroke-width: 1.2; }
#pd-graph [data-id] { cursor: pointer; }
#pd-graph.is-focused [data-id]:not(.is-on) { opacity: .15; }
#pd-graph.is-focused path:not(.is-on) { opacity: .08; }
#pd-graph path.is-on { stroke: var(--accent); stroke-width: 2.4; }
#pd-graph [data-id].is-on rect.box { stroke: var(--accent); stroke-width: 2; }
table { border-collapse: collapse; width: 100%; } td, th { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }
a { color: inherit; text-decoration-color: var(--accent); text-underline-offset: 2px; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .9em; }
details { border: 1px solid var(--line); border-radius: 8px; padding: 10px 14px; margin-bottom: 10px; background: var(--soft); }
summary { cursor: pointer; font-weight: 700; }
"""


# ============================================================
# ========================== BANTUAN =========================
# ============================================================


def esc(text):
    """
    Meloloskan teks untuk HTML.

    I.S. : text boleh None atau bukan string.
    F.S. : String aman untuk disisipkan di HTML dikembalikan.
    """
    return html.escape("" if text is None else str(text), quote=True)


def _owner_style(owner):
    """
    Membuat atribut style yang memasang warna pelaku.

    I.S. : owner adalah developer, ai, script, atau council.
    F.S. : String atribut style dikembalikan.
    """
    return f' style="--own: var(--own-{esc(owner or "script")})"'


def _theme(proj_dir):
    """
    Mengambil warna proyek dari tokens.json untuk tema halaman.

    I.S. : tokens.json boleh belum ada.
    F.S. : dict warna ink, paper, accent, accent_ink, muted dikembalikan, dengan nilai bawaan.
    """
    colors = {"ink": "#1c1917", "paper": "#faf7f2", "accent": "#c2410c", "accent_ink": "#ffffff", "muted": "#57534e"}
    tokens_path = proj_dir / "tokens.json"

    if tokens_path.is_file():
        group = io.read_json(tokens_path).get("color", {})

        for key in colors:
            entry = group.get(key.replace("_", "-"), {})
            value = entry.get("$value") if isinstance(entry, dict) else None

            if isinstance(value, str) and value.startswith("#"):
                colors[key] = value

    return colors


def _style(proj_dir):
    """
    Mengisi CSS halaman dengan warna proyek.

    I.S. : STYLE memuat penanda __ink__, __paper__, __accent__, __accent_ink__, __muted__.
    F.S. : CSS siap pakai dikembalikan.
    """
    css = STYLE

    for key, value in _theme(proj_dir).items():
        css = css.replace(f"__{key}__", value)

    return css


# ============================================================
# ========================== BAGIAN ==========================
# ============================================================


def _steps_section(proj_dir, decisions, text, deep=False):
    """
    Menyusun peta delapan langkah, diwarnai menurut pelakunya.

    I.S. : decisions adalah isi decisions.yaml (boleh kosong).
    F.S. : HTML bagian langkah kerja dikembalikan.
    """
    picked = any(d.get("source") == "client-picked" for d in decisions.get("decisions", []))
    items = []

    for number, (name, owner, marker) in enumerate(zip(text["step_names"], STEP_OWNERS, STEP_MARKERS), start=1):
        owner = owner or ("developer" if picked else "script")

        # Di mode deep, arah dan isi teks diputuskan dewan
        if deep and number in (3, 5):
            owner = "council"
        done = paths.has_site_content(paths.site_dir(proj_dir)) if marker == "site" else (proj_dir / marker).exists()
        state = text["done"] if done else text["pending"]
        css = "" if done else ' class="is-pending"'
        items.append(f'<li{css}{_owner_style(owner)}><b>{number}. {esc(name)}</b><small>{esc(text["owners"][owner])} · {esc(state)}</small></li>')

    legend = "".join(f"<li{_owner_style(k)}>{esc(v)}</li>" for k, v in text["owners"].items())

    return (
        f'<h2>{esc(text["steps"])}</h2><p class="note">{esc(text["steps_note"])}</p>'
        f'<ol class="steps">{"".join(items)}</ol><ul class="legend">{legend}</ul>'
    )


def _agency_section(context_graph, text):
    """
    Menyusun batang pembagian peran atas kebutuhan dan keputusan (sinyal P1 Agentivism).

    I.S. : context_graph adalah hasil graph.build().
    F.S. : HTML bagian pembagian peran dikembalikan; kosong bila belum ada simpul.
    """
    counted = [n for n in context_graph["nodes"] if n["type"] in ("requirement", "decision")]

    if not counted:
        return ""

    totals = {}

    for node in counted:
        totals[node["owner"]] = totals.get(node["owner"], 0) + 1

    spans = "".join(
        f'<span style="--own: var(--own-{esc(owner)}); flex: {count}" title="{esc(text["owners"][owner])}: {count}"></span>'
        for owner, count in totals.items()
    )
    parts = ", ".join(f"{text['owners'][owner]} {count}" for owner, count in totals.items())

    return (
        f'<h2>{esc(text["agency"])}</h2><p class="note">{esc(text["agency_note"])} {esc(parts)}.</p>'
        f'<div class="bar">{spans}</div>'
    )


def _field_text(value):
    """
    Menulis nilai satu kolom arah sebagai teks, termasuk peta layout.

    I.S. : value boleh string, dict, atau None.
    F.S. : Teks dikembalikan, atau None bila value None.
    """
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items())

    return value


def _council_section(context_graph, brief, text):
    """
    Menyusun bagian musyawarah dewan AI, khusus mode deep work.

    I.S. : context_graph berisi simpul minutes untuk sidang yang sudah dicatat.
    F.S. : HTML bagian dikembalikan; kosong bila mode bukan deep.
    """
    if brief.get("mode") != "deep":
        return ""

    held = {n["label"]: n for n in context_graph["nodes"] if n["type"] == "minutes"}
    rows = []

    for sitting, name in text["sittings"].items():
        node = held.get(sitting)

        if node is None:
            rows.append(f"<tr><td>{esc(name)}</td><td colspan=\"2\">{esc(text['not_held'])}</td></tr>")
            continue

        how = text["methods"].get(node.get("method"), node.get("method"))
        how += f" · {text['simulated']}" if node.get("simulated") else ""
        link = f'<a href="{esc(node["file"])}">{esc(text["minutes"])}</a>'
        rows.append(f"<tr><td>{esc(name)}</td><td>{esc(how)} → <b>{esc(node.get('outcome'))}</b></td>"
                    f"<td>{esc(node.get('why'))} ({link})</td></tr>")

    return (
        f'<h2>{esc(text["council"])}</h2><p class="note">{esc(text["council_note"])}</p>'
        f'<table>{"".join(rows)}</table>'
    )


def _support_section(proj_dir, brief, text):
    """
    Menyusun bagian tingkat dukungan dan hasil checkpoint, khusus mode terpandu.

    I.S. : brief adalah isi brief.yaml.
    F.S. : HTML bagian dikembalikan; kosong bila mode bukan guided.
    """
    if brief.get("mode") != "guided":
        return ""

    lang = "id" if project.first_language(brief) == "id" else "en"
    level = guided.project_level(brief)
    results = guided.results_from_trace(trace.read(proj_dir))
    rows = "".join(
        f"<tr><td>{esc(guided.CHECKPOINT_NAMES[lang][name])}</td><td>{esc(guided.RESULT_NAMES[lang][results.get(name)])}</td></tr>"
        for name in guided.CHECKPOINTS
    )
    history = guided.load_profile()["history"]
    upcoming = ""

    # Tingkat berikutnya hanya pasti setelah handoff mencatat proyek ini sebagai yang terakhir
    if history and history[-1].get("project") == str(proj_dir.resolve()):
        new_level = guided.load_profile()["support_level"]
        upcoming = f'<p>{esc(text["next_level"])}: {esc(guided.LEVEL_NAMES[lang][new_level])} ({new_level})</p>'

    return (
        f'<h2>{esc(text["support"])}</h2><p class="note">{esc(text["support_note"])}</p>'
        f'<p><b>{esc(guided.LEVEL_NAMES[lang][level])} ({level})</b></p><table>{rows}</table>{upcoming}'
    )


def _alternatives(decision, directions, current):
    """
    Mengumpulkan pilihan dari kelima arah untuk poros keputusan ini.

    I.S. : directions adalah daftar arah dari directions.yaml; current adalah arah terpilih
           beserta overrides (boleh None).
    F.S. : Daftar (nilai, peluang, dipilih) dikembalikan, nilai yang sama digabung. Pilihan
           saat ini yang tidak ada di kelima arah ditambahkan dengan peluang None.
    """
    field = AXIS_FIELDS.get(decision.get("axis"))
    now = _field_text((current or {}).get(field)) if field else None
    options = {}

    for direction in directions if field else []:
        value = _field_text(direction.get(field))

        if value is not None:
            options[value] = options.get(value, 0.0) + float(direction.get("probability", 0))

    found = [(value, prob, value == now) for value, prob in options.items()]

    if now is not None and now not in options:
        found.append((now, None, True))

    return found


def _check_status(context_graph, check_id, has_report, text):
    """
    Menentukan status satu check dari temuan yang melanggarnya.

    I.S. : has_report True bila report.json sudah ada.
    F.S. : HTML status (lolos, gagal, atau belum diperiksa) dikembalikan.
    """
    if not has_report:
        return f'<span>{esc(text["not_checked"])}</span>'

    failed = any(e["to"] == check_id and e["type"] == "violates" for e in context_graph["edges"])

    return f'<span class="bad">✗ {esc(text["failed"])}</span>' if failed else f'<span class="ok">✓ {esc(text["passed"])}</span>'


def _decision_card(context_graph, node, directions, current, has_report, text):
    """
    Menyusun satu kartu keputusan: pilihan, alasan, dasar, pelaku, alternatif, dampak, check.

    I.S. : node adalah simpul keputusan.
    F.S. : HTML satu kartu dikembalikan.
    """
    nodes = graph.index(context_graph)
    edges = context_graph["edges"]
    reqs = [nodes[e["to"]] for e in edges if e["from"] == node["id"] and e["type"] == "based_on"]
    checks = [nodes[e["to"]] for e in edges if e["from"] == node["id"] and e["type"] == "verified_by"]
    affected = [nodes[n] for n, *_ in graph.impact(context_graph, node["id"]) if nodes[n]["type"] in ("token", "section", "style")]
    source = text["sources"].get(node.get("source"), node.get("source") or "")
    axis = text["axes"].get(node.get("axis"), node.get("axis"))

    rows = [
        f'<dt>{esc(text["why"])}</dt><dd>{esc(node.get("why"))}</dd>',
        f'<dt>{esc(text["based_on"])}</dt><dd><ul>{"".join("<li>" + esc(r["label"]) + "</li>" for r in reqs)}</ul></dd>',
        f'<dt>{esc(text["decided_by"])}</dt><dd>{esc(text["owners"][node["owner"]])} ({esc(source)})</dd>',
    ]

    if node.get("accepted_by"):
        move = text["moves"].get(node.get("verification"), node.get("verification") or "")
        rows.append(f'<dt>{esc(text["accepted"])}</dt><dd>{esc(text["owners"][node["accepted_by"]])} · {esc(move)}</dd>')

    options = _alternatives(node, directions, current)

    if options:
        items = "".join(
            f'<li{" class=chosen" if chosen else ""}>{esc(value)} · '
            f'{esc(text["not_in_directions"]) if prob is None else str(round(prob * 100)) + "%"}'
            f'{" · " + esc(text["chosen"]) if chosen else ""}</li>'
            for value, prob, chosen in options
        )
        rows.append(f'<dt>{esc(text["alternatives"])}</dt><dd><ul>{items}</ul></dd>')

    if affected:
        rows.append(f'<dt>{esc(text["impact"])}</dt><dd>{esc(", ".join(a["label"] for a in affected))}</dd>')

    if checks:
        items = "".join(f'<li><code>{esc(c["label"])}</code> {_check_status(context_graph, c["id"], has_report, text)}</li>' for c in checks)
        rows.append(f'<dt>{esc(text["checks"])}</dt><dd><ul>{items}</ul></dd>')

    return (
        f'<article class="card"{_owner_style(node["owner"])}><h3>{esc(axis)}: {esc(node.get("choice"))}</h3>'
        f'<dl>{"".join(rows)}</dl>'
        f'<button type="button" data-focus="{esc(node["id"])}">{esc(text["show_in_graph"])}</button></article>'
    )


def _decisions_section(proj_dir, context_graph, text):
    """
    Menyusun semua kartu keputusan.

    I.S. : context_graph sudah berisi simpul keputusan (boleh kosong).
    F.S. : HTML bagian keputusan dikembalikan; kosong bila belum ada keputusan.
    """
    decisions = [n for n in context_graph["nodes"] if n["type"] == "decision"]

    if not decisions:
        return ""

    directions_path = proj_dir / "directions.yaml"
    directions = (io.read_yaml(directions_path) or {}).get("directions", []) if directions_path.is_file() else []
    decisions_data = io.read_yaml(proj_dir / "decisions.yaml") or {}
    current = project.effective_direction(decisions_data, {"directions": directions})
    has_report = (proj_dir / "report.json").is_file()
    cards = "".join(_decision_card(context_graph, n, directions, current, has_report, text) for n in decisions)

    return f'<h2>{esc(text["decisions"])}</h2><div class="cards">{cards}</div>'


def _visible_nodes(context_graph):
    """
    Memilih simpul yang digambar: semua kecuali halaman dan token yang tidak terkait keputusan.

    I.S. : context_graph adalah hasil graph.build().
    F.S. : (daftar simpul tampil, jumlah token tersembunyi) dikembalikan.
    """
    linked = {e["to"] for e in context_graph["edges"] if e["type"] in ("realized_by", "about")}
    shown, hidden = [], 0

    for node in context_graph["nodes"]:
        if node["type"] == "page":
            continue

        if node["type"] == "token" and node["id"] not in linked:
            hidden += 1
            continue

        shown.append(node)

    return shown, hidden


def _graph_svg(context_graph, text):
    """
    Menggambar graf sebagai SVG berkolom, dengan posisi yang dihitung di sini.

    I.S. : context_graph adalah hasil graph.build().
    F.S. : (HTML SVG, jumlah token tersembunyi) dikembalikan.
    """
    shown, hidden = _visible_nodes(context_graph)
    column_of = {kind: i for i, kinds in enumerate(COLUMNS) for kind in kinds}
    rows = [0] * len(COLUMNS)
    place = {}

    for node in shown:
        col = column_of[node["type"]]
        place[node["id"]] = (col * COLUMN_WIDTH + 12, TOP + rows[col] * ROW_HEIGHT)
        rows[col] += 1

    width = len(COLUMNS) * COLUMN_WIDTH
    height = TOP + max(rows + [1]) * ROW_HEIGHT + 12
    parts = [f'<text class="col" x="{i * COLUMN_WIDTH + 12}" y="24">{esc(h)}</text>' for i, h in enumerate(text["columns"])]

    for edge in context_graph["edges"]:
        if edge["from"] not in place or edge["to"] not in place:
            continue

        (x1, y1), (x2, y2) = sorted([place[edge["from"]], place[edge["to"]]])
        start_x = x1 + (NODE_WIDTH if x2 > x1 else 0)
        mid = (start_x + x2) / 2 if x2 > x1 else x1 - 30
        parts.append(
            f'<path data-edge="{esc(edge["from"])} {esc(edge["to"])}" '
            f'd="M{start_x} {y1 + 11} C{mid} {y1 + 11} {mid} {y2 + 11} {x2} {y2 + 11}"/>'
        )

    for node in shown:
        x, y = place[node["id"]]
        label = node["label"] if len(node["label"]) <= 30 else node["label"][:29] + "…"
        tip = f"{node['id']}: {node.get('why', node['label'])}"
        parts.append(
            f'<g data-id="{esc(node["id"])}"><title>{esc(tip)}</title>'
            f'<rect class="box" x="{x}" y="{y}" width="{NODE_WIDTH}" height="22" rx="4"/>'
            f'<rect class="own" x="{x}" y="{y}" width="5" height="22" rx="2" fill="var(--own-{esc(node["owner"])})"/>'
            f'<text x="{x + 12}" y="{y + 15}">{esc(label)}</text></g>'
        )

    svg = (
        f'<svg id="pd-graph" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" '
        f'aria-label="{esc(text["graph"])}">{"".join(parts)}</svg>'
    )

    return svg, hidden


def _graph_section(context_graph, text):
    """
    Menyusun bagian graf: tombol filter halaman, SVG, dan data untuk skrip sorotan.

    I.S. : context_graph adalah hasil graph.build().
    F.S. : HTML bagian graf dikembalikan.
    """
    svg, hidden = _graph_svg(context_graph, text)
    pages = [n for n in context_graph["nodes"] if n["type"] == "page"]
    buttons = [f'<button type="button" data-focus="">{esc(text["all_pages"])}</button>']

    for page in pages:
        sections = [e["to"] for e in context_graph["edges"] if e["from"] == page["id"] and e["type"] == "contains"]
        buttons.append(f'<button type="button" data-focus="{esc(" ".join(sections))}">{esc(page["label"])}</button>')

    data = {
        "edges": [[e["from"], e["to"], e["type"]] for e in context_graph["edges"]],
        "impactForward": sorted(graph.IMPACT_FORWARD),
        "impactBackward": sorted(graph.IMPACT_BACKWARD),
        "whyForward": sorted(graph.WHY_FORWARD),
        "whyBackward": sorted(graph.WHY_BACKWARD),
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    note = f'<p class="note">{hidden} {esc(text["hidden_tokens"])}.</p>' if hidden else ""

    return (
        f'<h2 id="graf">{esc(text["graph"])}</h2><p class="note">{esc(text["graph_note"])}</p>'
        f'<div class="filters">{"".join(buttons)}</div><div class="graph-wrap">{svg}</div>{note}'
        f'<script type="application/json" id="pd-graph-data">{payload}</script>'
    )


def _todo_section(proj_dir, context_graph, text):
    """
    Menyusun daftar placeholder yang tampil di situs, dan fakta kosong yang belum dipakai.

    I.S. : context_graph adalah hasil graph.build(); situs boleh belum di-scaffold.
    F.S. : HTML bagian isian yang masih kosong dikembalikan. Sebelum halaman diisi, daftar
           berasal dari celah fakta di graf beserta seksi yang akan memakainya.
    """
    site_ph = project.site_placeholders(paths.site_dir(proj_dir))
    nodes = graph.index(context_graph)
    placeholders = [n for n in context_graph["nodes"] if n["type"] == "placeholder"]
    rows = [f'<tr><td><code>{esc(t)}</code></td><td>{esc(text["used_in"])} {esc(", ".join(files))}</td></tr>'
            for t, files in site_ph.items()]

    for ph in placeholders:
        if site_ph and ph["label"] in site_ph:
            continue

        used = [nodes[e["to"]] for e in context_graph["edges"] if e["from"] == ph["id"] and e["type"] == "fills"]
        where = ", ".join(f'{u["page"]}#{u["label"]}' for u in used) or "—"
        label = text["not_on_site"] if site_ph else f'{text["used_in"]} {where}'
        rows.append(f'<tr><td><code>{esc(ph["label"])}</code></td><td>{esc(label)}</td></tr>')

    if not rows:
        return f'<h2>{esc(text["todo"])}</h2><p>{esc(text["todo_none"])}</p>'

    return (
        f'<h2>{esc(text["todo"])}</h2><p class="note">{esc(text["todo_note"])}</p>'
        f'<table>{"".join(rows)}</table>'
    )


def _quality_section(proj_dir, text):
    """
    Menyusun ringkasan hasil pemeriksaan dari report.json.

    I.S. : report.json boleh belum ada.
    F.S. : HTML bagian hasil pemeriksaan dikembalikan.
    """
    report_path = proj_dir / "report.json"

    if not report_path.is_file():
        return f'<h2>{esc(text["quality"])}</h2><p>{esc(text["quality_none"])}</p>'

    summary = io.read_json(report_path).get("summary", {})
    tfs = summary.get("tfs_auto")
    tfs_text = f" · {round(tfs * 100)}% {text['constraints']}" if isinstance(tfs, (int, float)) else ""

    return (
        f'<h2>{esc(text["quality"])}</h2>'
        f'<p>{summary.get("errors", 0)} {esc(text["errors"])} · {summary.get("warnings", 0)} {esc(text["warnings"])}{esc(tfs_text)}</p>'
    )


def _signals_section(proj_dir, brief):
    """
    Menyusun bagian sinyal Agentivism P1-P6, sama dengan bagian 7 HANDOFF.md.

    I.S. : Proyek punya brief.yaml.
    F.S. : HTML bagian dikembalikan.
    """
    lang = "id" if project.first_language(brief) == "id" else "en"
    title, intro, items = signals.lines(signals.compute(proj_dir), lang)

    return f'<h2>{esc(title)}</h2><p class="note">{esc(intro)}</p><ul>{"".join("<li>" + esc(i) + "</li>" for i in items)}</ul>'


def _chain_text(context_graph, visits):
    """
    Menulis hasil telusur sebagai daftar label, untuk jawaban soal.

    I.S. : visits adalah hasil graph.impact() atau graph.why().
    F.S. : HTML daftar dikembalikan.
    """
    nodes = graph.index(context_graph)
    items = []

    for node_id, *_ in visits:
        node = nodes[node_id]
        detail = f": {node['why']}" if node.get("why") and node["type"] in ("decision", "requirement") else ""
        items.append(f'<li><code>{esc(node["label"])}</code>{esc(detail)}</li>')

    return f'<ul>{"".join(items)}</ul>'


def _quiz_section(context_graph, text):
    """
    Menyusun dua soal: menjelaskan ulang satu keputusan dan menebak dampak satu token.

    I.S. : context_graph adalah hasil graph.build().
    F.S. : HTML bagian uji pemahaman dikembalikan; kosong bila belum ada keputusan.
    """
    nodes = context_graph["nodes"]
    decision = next((n for n in nodes if n["type"] == "decision" and n.get("axis") == "layout"), None)
    decision = decision or next((n for n in nodes if n["type"] == "decision"), None)

    if decision is None:
        return ""

    token = next((n for n in nodes if n["id"] == "token:color.accent"), None)
    axis = text["axes"].get(decision.get("axis"), decision.get("axis") or "").lower()
    blocks = [
        f'<details><summary>{esc(text["quiz_why"].format(axis=axis))}</summary>'
        f'<p><b>{esc(text["choice"])}:</b> {esc(decision.get("choice"))}</p>'
        f'<p><b>{esc(text["answer"])}:</b> {esc(decision.get("why"))}</p>'
        f'{_chain_text(context_graph, graph.why(context_graph, decision["id"]))}</details>'
    ]

    if token:
        blocks.append(
            f'<details><summary>{esc(text["quiz_impact"].format(label=token["label"]))}</summary>'
            f'{_chain_text(context_graph, graph.impact(context_graph, token["id"]))}</details>'
        )

    return f'<h2>{esc(text["quiz"])}</h2><p class="note">{esc(text["quiz_note"])}</p>{"".join(blocks)}'


# ============================================================
# ========================= HALAMAN ==========================
# ============================================================


def build_html(proj_dir):
    """
    Menyusun seluruh EXPLAIN.html dari graf konteks dan file proyek.

    I.S. : proj_dir berisi minimal brief.yaml.
    F.S. : String HTML mandiri dikembalikan; graph.json diperbarui; tidak ada file lain ditulis.
    """
    proj_dir = Path(proj_dir)
    brief = io.read_yaml(proj_dir / "brief.yaml") or {}
    lang = project.first_language(brief)
    text = TEXT.get(lang, TEXT["en"])
    context_graph = graph.refresh(proj_dir)
    decisions_path = proj_dir / "decisions.yaml"
    decisions = (io.read_yaml(decisions_path) or {}) if decisions_path.is_file() else {}
    name = (brief.get("business", {}).get("name") or {}).get("value") or paths.site_dir(proj_dir).name

    body = "".join([
        f'<h1>{esc(text["title"])}: {esc(name)}</h1><p class="note">{esc(text["intro"])}</p>',
        _steps_section(proj_dir, decisions, text, brief.get("mode") == "deep"),
        _agency_section(context_graph, text),
        _support_section(proj_dir, brief, text),
        _council_section(context_graph, brief, text),
        _decisions_section(proj_dir, context_graph, text),
        _graph_section(context_graph, text),
        _todo_section(proj_dir, context_graph, text),
        _quality_section(proj_dir, text),
        _signals_section(proj_dir, brief),
        _quiz_section(context_graph, text),
    ])

    return (
        f'<!doctype html>\n<html lang="{esc(lang)}">\n<head>\n<meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{esc(text["title"])}: {esc(name)}</title>\n'
        f'<style>{_style(proj_dir)}</style>\n</head>\n<body>\n<main>{body}</main>\n'
        f'<script>{SCRIPT}</script>\n</body>\n</html>\n'
    )


def write(proj_dir):
    """
    Menulis EXPLAIN.html ke folder proyek.

    I.S. : proj_dir berisi minimal brief.yaml.
    F.S. : <proj_dir>/EXPLAIN.html ditulis; path-nya dikembalikan.
    """
    path = Path(proj_dir) / EXPLAIN_FILE
    io.write_text(path, build_html(proj_dir))

    return path
