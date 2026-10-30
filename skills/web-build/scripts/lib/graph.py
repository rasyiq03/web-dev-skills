# ============================================================
# File      : graph.py
# Proyek    : ScaffolDev
# Deskripsi : Graf konteks proyek: kebutuhan, keputusan, token, seksi, file,
#             check, dan temuan beserta hubungannya. Dibangun ulang dari
#             file proyek, ditulis ke graph.json, dan bisa ditanya
#             dampak (--impact) serta alasan (--why) satu simpul.
# ============================================================

import json
from collections import deque
from pathlib import Path

from lib import io, paths, project

# ============================================================
# ========================= KONSTANTA ========================
# ============================================================

GRAPH_FILE = "graph.json"
GRAPH_VERSION = 1

# Grup token yang dicetak context.py, sesuai urutan lamanya
CONTEXT_TOKEN_GROUPS = ("color", "font", "weight", "size", "space", "border", "shadow", "motion")

# Arah telusur dampak: ikuti edge maju untuk jenis ini, dan mundur untuk jenis itu
IMPACT_FORWARD = {"realized_by", "verified_by", "located_in", "contains", "fills"}
IMPACT_BACKWARD = {"based_on", "about", "violates"}

# Arah telusur alasan: kebalikannya, tanpa 'about' (check tidak menjelaskan token)
WHY_FORWARD = {"based_on", "violates", "decided_in"}
WHY_BACKWARD = {"realized_by", "verified_by", "located_in", "contains", "fills"}

# Pemilik simpul menurut sumber datanya (mekanisme delegasi Agentivism)
OWNER_BY_SOURCE = {
    "stated": "developer",
    "client-picked": "developer",
    "inferred": "ai",
    "sampled": "script",
    "overridden": "developer",
    "council": "council",
}

# Jejak kerja; dibaca langsung di sini agar lib/trace.py bisa memanggil refresh()
TRACE_FILE = "trace.jsonl"


# ============================================================
# ======================= PEMBANGUN GRAF =====================
# ============================================================


class _Builder:
    """
    Penampung simpul dan edge selama graf dibangun, dengan urutan masuk yang tetap.
    """

    def __init__(self):
        """
        Menyiapkan daftar simpul dan edge kosong.

        I.S. : -
        F.S. : nodes dan edges kosong; indeks id siap.
        """
        self.nodes = []
        self.edges = []
        self._ids = {}
        self._edge_keys = set()

    def node(self, node_id, node_type, label, owner, **attrs):
        """
        Menambah satu simpul, atau mengembalikan yang sudah ada dengan id sama.

        I.S. : node_id unik per simpul.
        F.S. : Simpul ada di nodes; dict simpul dikembalikan.
        """
        if node_id in self._ids:
            return self._ids[node_id]

        entry = {"id": node_id, "type": node_type, "label": label, "owner": owner}
        entry.update({key: value for key, value in attrs.items() if value not in (None, "", [])})
        self.nodes.append(entry)
        self._ids[node_id] = entry

        return entry

    def edge(self, source, target, edge_type):
        """
        Menambah satu edge bila kedua ujungnya ada dan edge itu belum ada.

        I.S. : source dan target adalah id simpul.
        F.S. : Edge ditambahkan sekali saja; edge ke simpul yang tidak ada diabaikan.
        """
        key = (source, target, edge_type)

        if key in self._edge_keys or source not in self._ids or target not in self._ids:
            return

        self._edge_keys.add(key)
        self.edges.append({"from": source, "to": target, "type": edge_type})

    def has(self, node_id):
        """
        Memeriksa apakah simpul dengan id ini sudah ada.

        I.S. : -
        F.S. : True bila ada.
        """
        return node_id in self._ids


def _read_optional(proj_dir, name, reader):
    """
    Membaca satu file proyek bila ada.

    I.S. : reader adalah io.read_yaml atau io.read_json.
    F.S. : Isi file dikembalikan, atau dict kosong bila file belum ada.
    """
    path = proj_dir / name

    return (reader(path) or {}) if path.is_file() else {}


def _layout_map(decisions):
    """
    Memetakan id seksi ke id pola dari keputusan layout.

    I.S. : decisions adalah isi decisions.yaml.
    F.S. : dict {seksi: pola} dikembalikan; kosong bila tidak ada keputusan layout.
    """
    chosen = decisions.get("chosen", {}).get("layout")

    if isinstance(chosen, dict):
        return dict(chosen)

    layout = next((d for d in decisions.get("decisions", []) if d.get("axis") == "layout"), {})
    mapping = {}

    for pair in layout.get("choice", "").split(","):
        if "=" in pair:
            section, pattern = pair.split("=", 1)
            mapping[section.strip()] = pattern.strip()

    return mapping


def _add_requirements(builder, gaps):
    """
    Menambah simpul kebutuhan dan placeholder dari gaps.json.

    I.S. : gaps adalah isi gaps.json (boleh kosong).
    F.S. : Simpul requirement dan placeholder ada di builder.
    """
    for req in gaps.get("requirements", []):
        builder.node(
            req["id"], "requirement", f"{req.get('path')} = {req.get('value')}",
            OWNER_BY_SOURCE.get(req.get("source"), "ai"),
            why=f"source: {req.get('source')}", path=req.get("path"), value=req.get("value"),
        )

    for fact, text in gaps.get("placeholders", {}).items():
        builder.node(f"ph:{fact}", "placeholder", text, "script", fact=fact)


def _add_pages_and_sections(builder, brief, site_type, decisions, has_site):
    """
    Menambah simpul halaman dan seksi beserta polanya, dan menautkan placeholder ke seksi.

    I.S. : site_type adalah isi file tipe situs; has_site True bila situs sudah di-scaffold.
    F.S. : Simpul page dan section ada; edge contains, located_in, dan fills tercatat.
    """
    patterns_all = project.load_patterns()
    layout = _layout_map(decisions)

    for page in project.site_pages(brief, site_type):
        page_file = paths.page_file(page)
        builder.node(f"page:{page}", "page", page_file, "script", file=page_file)

        if has_site:
            builder.node(f"file:{page_file}", "file", page_file, "script")
            builder.edge(f"page:{page}", f"file:{page_file}", "located_in")

    for sec in site_type.get("sections", []):
        sec_id, page = sec["id"], sec.get("page")
        pattern = layout.get(sec_id, "")
        kind_patterns = patterns_all.get(sec.get("pattern_kind", ""), {})
        description = kind_patterns.get(pattern, {}).get("layout", "") if pattern else sec.get("purpose", "")
        node_id = f"section:{page}#{sec_id}"

        builder.node(
            node_id, "section", sec_id, "script",
            why=sec.get("purpose"), page=page, pattern=pattern, layout=description,
        )
        builder.edge(f"page:{page}", node_id, "contains")

        if has_site:
            builder.edge(node_id, f"file:{paths.page_file(page)}", "located_in")

        for fact in sec.get("facts", []):
            builder.edge(f"ph:{fact}", node_id, "fills")


def _add_tokens(builder, tokens, has_site):
    """
    Menambah simpul token dari tokens.json, dengan urutan file aslinya.

    I.S. : tokens adalah isi tokens.json (boleh kosong).
    F.S. : Simpul token ada; bila situs ada, setiap token terhubung ke css/tokens.css.
    """
    if has_site:
        builder.node("file:css/tokens.css", "file", "css/tokens.css", "script")

    for group, entries in tokens.items():
        if group.startswith("$") or not isinstance(entries, dict):
            continue

        for name, entry in entries.items():
            value = entry.get("$value") if isinstance(entry, dict) else entry
            node_id = f"token:{group}.{name}"
            builder.node(node_id, "token", f"--pd-{group}-{name}", "script", group=group, value=value)

            if has_site:
                builder.edge(node_id, "file:css/tokens.css", "located_in")


def _add_style(builder, decision):
    """
    Menambah simpul gaya dengan komponen dan signature move-nya.

    I.S. : decision adalah keputusan berporos style.
    F.S. : Simpul style ada dan terhubung dari keputusan itu lewat realized_by.
    """
    style_id = decision.get("choice", "")
    style = project.load_style(style_id) or {}

    builder.node(
        f"style:{style_id}", "style", style_id, "script",
        components=style.get("components"), signature=style.get("signature_moves"),
    )
    builder.edge(decision["id"], f"style:{style_id}", "realized_by")


def _judgements(proj_dir):
    """
    Mengambil peristiwa accept atau decide terakhir per keputusan dari trace.jsonl.

    I.S. : trace.jsonl boleh belum ada.
    F.S. : dict {id keputusan: peristiwa terakhir} dikembalikan.
    """
    path = Path(proj_dir) / TRACE_FILE
    found = {}

    if not path.is_file():
        return found

    for line in io.read_text(path).splitlines():
        entry = json.loads(line) if line.strip() else {}

        if entry.get("event") in ("accept", "decide") and entry.get("decision"):
            found[entry["decision"]] = entry

    return found


def _add_decisions(builder, decisions, judgements):
    """
    Menambah simpul keputusan, check, dan edge based_on, realized_by, verified_by, about.

    I.S. : Simpul requirement, token, dan section sudah ada di builder; judgements adalah
           hasil _judgements().
    F.S. : Simpul decision dan check ada, dengan siapa yang menerima atau mengubahnya; edge
           ke simpul yang tidak dikenal diabaikan.
    """
    sections_by_pattern = {}

    for node in builder.nodes:
        if node["type"] == "section" and node.get("pattern"):
            sections_by_pattern.setdefault(node["pattern"], []).append(node["id"])

    for constraint in decisions.get("constraints", []):
        builder.node(
            f"check:{constraint['id']}", "check", constraint["id"], "script",
            kind=constraint.get("kind"),
        )

        for key in ("token", "fg", "bg"):
            if constraint.get(key):
                builder.edge(f"check:{constraint['id']}", f"token:{constraint[key]}", "about")

    for dec in decisions.get("decisions", []):
        judged = judgements.get(dec["id"], {})
        owner = OWNER_BY_SOURCE.get(dec.get("source"), "ai")

        # Keputusan yang diubah dimiliki pengubahnya; yang diterima tetap milik pembuatnya
        if judged.get("event") == "decide":
            owner = judged.get("by", owner)

        builder.node(
            dec["id"], "decision", f"{dec.get('axis')}: {dec.get('choice')}", owner,
            why=dec.get("rationale"), axis=dec.get("axis"), choice=dec.get("choice"),
            source=dec.get("source"), accepted_by=judged.get("by"),
            verification=judged.get("verification"),
        )

        for req_id in dec.get("based_on", []):
            builder.edge(dec["id"], req_id, "based_on")

        if dec.get("axis") == "style":
            _add_style(builder, dec)

        # Semua warna, termasuk warna grafik dan status, diturunkan dari palet
        if dec.get("axis") == "palette":
            for node in list(builder.nodes):
                if node["type"] == "token" and node.get("group") == "color":
                    builder.edge(dec["id"], node["id"], "realized_by")

        for target in dec.get("realized_by", []):
            builder.edge(dec["id"], f"token:{target}", "realized_by")

            for section_id in sections_by_pattern.get(target, []):
                builder.edge(dec["id"], section_id, "realized_by")

        for check_id in dec.get("verified_by", []):
            builder.edge(dec["id"], f"check:{check_id}", "verified_by")


def _add_minutes(builder, proj_dir):
    """
    Menambah simpul notulen sidang dewan yang sudah dicatat, dan edge decided_in.

    I.S. : Simpul keputusan sudah ada; peristiwa council di trace.jsonl menandai sidang
           yang notulennya lolos pemeriksaan.
    F.S. : Satu simpul minutes:<sidang> per sidang tercatat; keputusan bersumber council
           (sidang arah) dan keputusan yang disebut di notulen terhubung lewat decided_in.
    """
    path = Path(proj_dir) / TRACE_FILE
    recorded = {}

    if path.is_file():
        for line in io.read_text(path).splitlines():
            entry = json.loads(line) if line.strip() else {}

            if entry.get("event") == "council":
                recorded[entry["sitting"]] = entry

    for sitting, entry in recorded.items():
        minutes_path = Path(proj_dir) / "deliberation" / f"{sitting}.yaml"
        minutes = (io.read_yaml(minutes_path) or {}) if minutes_path.is_file() else {}
        node_id = f"minutes:{sitting}"

        builder.node(
            node_id, "minutes", sitting, "council",
            why=(minutes.get("resolution") or {}).get("summary"), method=entry.get("method"),
            outcome=entry.get("outcome"), simulated=entry.get("simulated"), file=f"deliberation/{sitting}.yaml",
        )

        for node in list(builder.nodes):
            if node["type"] == "decision" and (node["id"] in minutes.get("decisions", [])
                                               or (sitting == "direction" and node.get("source") == "council")):
                builder.edge(node["id"], node_id, "decided_in")


def _add_findings(builder, report_data):
    """
    Menambah simpul temuan dari report.json dan menautkannya ke check atau file.

    I.S. : report_data adalah isi report.json (boleh kosong).
    F.S. : Temuan constraint melanggar check-nya; temuan lain terhubung ke file-nya.
    """
    for number, finding in enumerate(report_data.get("findings", []), start=1):
        node_id = f"finding:{number}"
        rule = finding.get("rule", "")

        builder.node(
            node_id, "finding", rule, "script",
            why=finding.get("message"), level=finding.get("level"),
            file=finding.get("file"), line=finding.get("line"),
        )

        if rule.startswith("constraint-"):
            builder.edge(node_id, f"check:{rule[len('constraint-'):]}", "violates")
        elif finding.get("file"):
            builder.node(f"file:{finding['file']}", "file", finding["file"], "script")
            builder.edge(node_id, f"file:{finding['file']}", "located_in")


def build(proj_dir):
    """
    Membangun graf konteks dari file proyek yang sudah ada.

    I.S. : proj_dir adalah folder kerja (.ScaffolDev) berisi minimal brief.yaml; file lain
           boleh belum ada; situs di folder induknya.
    F.S. : dict graf {version, project, nodes, edges} dikembalikan; tidak ada file ditulis.
    """
    proj_dir = Path(proj_dir)
    brief = _read_optional(proj_dir, "brief.yaml", io.read_yaml)
    gaps = _read_optional(proj_dir, "gaps.json", io.read_json)
    decisions = _read_optional(proj_dir, "decisions.yaml", io.read_yaml)
    tokens = _read_optional(proj_dir, "tokens.json", io.read_json)
    report_data = _read_optional(proj_dir, "report.json", io.read_json)
    has_site = paths.has_site_content(paths.site_dir(proj_dir))

    builder = _Builder()
    _add_requirements(builder, gaps)

    if brief.get("site_type"):
        site_type = project.load_site_type(brief["site_type"])
        _add_pages_and_sections(builder, brief, site_type, decisions, has_site)

    _add_tokens(builder, tokens, has_site)
    _add_decisions(builder, decisions, _judgements(proj_dir))
    _add_minutes(builder, proj_dir)
    _add_findings(builder, report_data)

    return {"version": GRAPH_VERSION, "project": paths.site_dir(proj_dir).name, "nodes": builder.nodes, "edges": builder.edges}


def refresh(proj_dir):
    """
    Membangun ulang graf dan menulisnya ke graph.json.

    I.S. : proj_dir adalah folder proyek yang ada.
    F.S. : <proj_dir>/graph.json berisi graf terbaru; graf dikembalikan.
    """
    graph = build(proj_dir)
    io.write_json(Path(proj_dir) / GRAPH_FILE, graph)

    return graph


# ============================================================
# ======================== PERTANYAAN ========================
# ============================================================


def index(graph):
    """
    Membuat indeks simpul per id.

    I.S. : graph adalah hasil build().
    F.S. : dict {id: simpul} dikembalikan.
    """
    return {node["id"]: node for node in graph["nodes"]}


def resolve(graph, name):
    """
    Mencari id simpul dari nama yang diketik pengguna.

    I.S. : name bisa id lengkap (token:color.accent) atau tanpa awalan (color.accent).
    F.S. : id simpul dikembalikan, atau None bila tidak ditemukan atau ambigu.
    """
    nodes = index(graph)

    if name in nodes:
        return name

    matches = [node_id for node_id in nodes if node_id.split(":", 1)[-1] == name]

    return matches[0] if len(matches) == 1 else None


def _walk(graph, start, forward, backward):
    """
    Menelusuri graf dari satu simpul, melebar, tanpa mengunjungi simpul dua kali.

    I.S. : forward dan backward adalah himpunan jenis edge yang diikuti ke arah masing-masing.
    F.S. : Daftar (id simpul, jenis edge, id asal, maju) dikembalikan sesuai urutan kunjungan;
           maju False berarti edge itu ditelusuri dari ujung ke pangkal.
    """
    seen = {start}
    queue = deque([start])
    visits = []

    while queue:
        current = queue.popleft()

        for edge in graph["edges"]:
            if edge["from"] == current and edge["type"] in forward:
                found, is_forward = edge["to"], True
            elif edge["to"] == current and edge["type"] in backward:
                found, is_forward = edge["from"], False
            else:
                continue

            if found not in seen:
                seen.add(found)
                queue.append(found)
                visits.append((found, edge["type"], current, is_forward))

    return visits


def impact(graph, start):
    """
    Mencari semua simpul yang terdampak bila simpul start berubah (pedoman G16).

    I.S. : start adalah id simpul yang ada.
    F.S. : Daftar (id simpul, jenis edge, id asal, maju) dikembalikan.
    """
    return _walk(graph, start, IMPACT_FORWARD, IMPACT_BACKWARD)


def why(graph, start):
    """
    Mencari rantai alasan di hulu simpul start (pedoman G11).

    I.S. : start adalah id simpul yang ada.
    F.S. : Daftar (id simpul, jenis edge, id asal, maju) dikembalikan, dari yang terdekat.
    """
    return _walk(graph, start, WHY_FORWARD, WHY_BACKWARD)


def describe(node):
    """
    Menulis satu simpul sebagai satu baris yang mudah dibaca.

    I.S. : node adalah dict simpul.
    F.S. : String '<id> (<label>), oleh <owner>: <why>' dikembalikan.
    """
    text = f"{node['id']} ({node['label']}), oleh {node['owner']}"

    return f"{text}: {node['why']}" if node.get("why") else text


def _page_placeholders(graph, page):
    """
    Mencari placeholder yang mengisi seksi halaman ini.

    I.S. : page adalah id halaman.
    F.S. : Daftar simpul placeholder dikembalikan, urut seperti di graf.
    """
    prefix = f"section:{page}#"
    used = {edge["from"] for edge in graph["edges"] if edge["type"] == "fills" and edge["to"].startswith(prefix)}

    return [node for node in graph["nodes"] if node["id"] in used]


def page_view(graph, page):
    """
    Mengambil bagian graf yang dibutuhkan untuk membangun satu halaman.

    I.S. : page adalah id halaman yang ada di graf.
    F.S. : dict {sections, decisions, tokens, style, placeholders} dikembalikan.
    """
    nodes = graph["nodes"]
    style = next((node for node in nodes if node["type"] == "style"), {})

    return {
        "sections": [node for node in nodes if node["type"] == "section" and node.get("page") == page],
        "decisions": [node for node in nodes if node["type"] == "decision"],
        "tokens": [
            node for group in CONTEXT_TOKEN_GROUPS for node in nodes
            if node["type"] == "token" and node.get("group") == group
        ],
        "style": style,
        "placeholders": [node for node in nodes if node["type"] == "placeholder"],
        "page_placeholders": _page_placeholders(graph, page),
    }
