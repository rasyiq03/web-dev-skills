# ============================================================
# File      : export_rdf.py
# Proyek    : ScaffolDev
# Deskripsi : Mengekspor kebutuhan, keputusan, alasan, token, dan batasan
#             satu proyek ke RDF (Turtle), menulis setiap batasan sebagai
#             shape SHACL, memvalidasinya dengan pySHACL terhadap fakta yang
#             diambil dari situs, lalu membandingkan hasilnya dengan tfs_auto
#             dari check.py (IMPLEMENTATION.md §3.12).
# ============================================================

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "skills" / "web-build" / "scripts"))

from bs4 import BeautifulSoup  # noqa: E402
from lib import audit_rules, color, io, paths, project, report  # noqa: E402
from lib.report import EXIT_CHECK_FAILED, EXIT_INVALID, fail  # noqa: E402

try:
    from pyshacl import validate
    from rdflib import RDF, XSD, BNode, Graph, Literal, Namespace, URIRef
except ImportError:  # pragma: no cover - pesan untuk pengguna
    print("rdflib dan pyshacl belum terpasang.")
    print("NEXT: pip install -r requirements-dev.txt, then run export_rdf again")
    sys.exit(1)

SD = Namespace("https://scaffoldev.dev/ontology#")
SF = Namespace("https://scaffoldev.dev/facts#")
SH = Namespace("http://www.w3.org/ns/shacl#")
SHAPES = REPO_ROOT / "tools" / "shapes.ttl"


def normal(value):
    """
    Menyamakan penulisan nilai token: spasi di tepi dibuang, warna heksadesimal huruf kecil.

    I.S. : value teks nilai CSS atau token.
    F.S. : Teks yang bisa dibandingkan langsung dikembalikan.
    """
    text = str(value).strip()
    return text.lower() if re.fullmatch(r"#[0-9A-Fa-f]{3,8}", text) else text


def node(base, kind, name):
    """
    Membuat URI simpul proyek.

    I.S. : base adalah namespace proyek; kind dan name teks.
    F.S. : URIRef stabil dikembalikan, misalnya <urn:scaffoldev:kopi-senja:decision/d-style-1>.
    """
    return URIRef(f"{base}{kind}/{re.sub(r'[^A-Za-z0-9._-]', '_', name)}")


# ============================================================
# =========================== MODEL ==========================
# ============================================================


def build_model(proj_dir, slug):
    """
    Menyusun graf model: kebutuhan, keputusan dan alasannya, token, dan batasan.

    I.S. : gaps.json, decisions.yaml, dan tokens.json ada di folder kerja.
    F.S. : Graf rdflib dikembalikan.
    """
    base = f"urn:scaffoldev:{slug}:"
    g = Graph()
    g.bind("sd", SD)
    gaps = io.read_json(proj_dir / "gaps.json")
    decisions = io.read_yaml(proj_dir / "decisions.yaml")
    tokens = io.read_json(proj_dir / "tokens.json")

    for req in gaps.get("requirements", []):
        r = node(base, "requirement", req["id"])
        g.add((r, RDF.type, SD.Requirement))
        g.add((r, SD.path, Literal(req.get("path", ""))))
        g.add((r, SD.value, Literal(str(req.get("value")))))
        g.add((r, SD.source, Literal(req.get("source", ""))))

    for group, entries in tokens.items():
        if group.startswith("$"):
            continue
        for name, entry in entries.items():
            t = node(base, "token", f"{group}.{name}")
            g.add((t, RDF.type, SD.Token))
            g.add((t, SD.cssVar, Literal(f"--pd-{group}-{name}")))
            g.add((t, SD.value, Literal(str(entry.get("value")))))

    for c in decisions.get("constraints", []):
        cn = node(base, "constraint", c["id"])
        g.add((cn, RDF.type, SD.Constraint))
        for key, value in c.items():
            if key != "id":
                g.add((cn, SD[key], Literal(value)))

    for d in decisions.get("decisions", []):
        dn = node(base, "decision", d["id"])
        g.add((dn, RDF.type, SD.Decision))
        g.add((dn, SD.axis, Literal(d.get("axis", ""), datatype=XSD.string)))
        g.add((dn, SD.choice, Literal(str(d.get("choice")))))
        g.add((dn, SD.source, Literal(d.get("source", ""))))
        rationale = node(base, "rationale", d["id"])
        g.add((rationale, RDF.type, SD.Rationale))
        g.add((rationale, SD.text, Literal(d.get("rationale", ""), datatype=XSD.string)))
        g.add((dn, SD.justifiedBy, rationale))
        for req_id in d.get("based_on", []):
            g.add((dn, SD.basedOn, node(base, "requirement", req_id)))
        for target in d.get("realized_by", []):
            kind = "token" if "." in target else "pattern"
            g.add((dn, SD.realizedBy, node(base, kind, target)))
        for c_id in d.get("verified_by", []):
            g.add((dn, SD.verifiedBy, node(base, "constraint", c_id)))

    return g


# ============================================================
# ========================== FAKTA ===========================
# ============================================================


def css_rules(site_dir):
    """
    Membaca aturan CSS situs sebagai (berkas, selektor, properti, nilai).

    I.S. : site_dir/css berisi stylesheet.
    F.S. : Daftar deklarasi dikembalikan; komentar dibuang, @media diratakan.
    """
    rules = []
    for css in sorted((site_dir / "css").rglob("*.css")):
        text = re.sub(r"/\*.*?\*/", "", io.read_text(css), flags=re.DOTALL)
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
            for selector in (s.strip() for s in match.group(1).split(",")):
                for decl in match.group(2).split(";"):
                    if ":" in decl:
                        prop, value = decl.split(":", 1)
                        rules.append((css.name, selector, prop.strip(), value.strip()))
    return rules


def build_facts(proj_dir, decisions):
    """
    Mengambil fakta dari situs yang sudah dibangun, bukan dari keputusan.

    I.S. : Situs proyek ada; decisions dari decisions.yaml (hanya untuk pasangan kontras).
    F.S. : Graf fakta dikembalikan: nilai token di css/tokens.css, deklarasi CSS, pola per
           halaman, rasio kontras pasangan yang diminta, jumlah transisi, dan kata sapaan.
    """
    site_dir = paths.site_dir(proj_dir)
    g = Graph()
    g.bind("sf", SF)
    site = SF.site
    g.add((site, RDF.type, SF.Site))

    tokens_css = site_dir / "css" / "tokens.css"
    declared = dict(re.findall(r"(--pd-[a-z0-9-]+)\s*:\s*([^;]+);", io.read_text(tokens_css))) if tokens_css.is_file() else {}
    for var, value in declared.items():
        t = SF[f"token{var}"]
        g.add((t, RDF.type, SF.Token))
        g.add((t, SF.cssVar, Literal(var)))
        g.add((t, SF.value, Literal(normal(value))))

    for index, (_, selector, prop, value) in enumerate(css_rules(site_dir)):
        d = SF[f"decl{index}"]
        g.add((site, SF.declares, d))
        g.add((d, SF.selector, Literal(selector)))
        g.add((d, SF.property, Literal(prop)))
        g.add((d, SF.value, Literal(value)))

    words = {"Anda": 0, "kamu": 0}
    for page in paths.site_files(site_dir, "*.html"):
        rel = page.relative_to(site_dir).as_posix()
        p = SF[f"page/{rel}"]
        g.add((p, RDF.type, SF.Page))
        soup = BeautifulSoup(io.read_text(page), "html.parser")
        for element in soup.find_all(attrs={"data-pd-pattern": True}):
            g.add((p, SF.pattern, Literal(element["data-pd-pattern"])))
        text = soup.get_text()
        for word in words:
            words[word] += len(re.findall(rf"\b{word}\b", text, re.IGNORECASE))
    for word, count in words.items():
        g.add((site, SF[f"uses_{word.lower()}"], Literal(count)))

    transitions = sum(1 for name, _, prop, _ in css_rules(site_dir)
                      if name != "base.css" and prop in ("transition", "animation"))
    g.add((site, SF.transitions, Literal(transitions)))

    for c in decisions.get("constraints", []):
        if c.get("kind") == "contrast-min":
            fg = declared.get(f"--pd-color-{c['fg'].split('.')[-1]}", "").strip()
            bg = declared.get(f"--pd-color-{c['bg'].split('.')[-1]}", "").strip()
            pair = SF[f"contrast/{c['id']}"]
            g.add((pair, RDF.type, SF.ContrastPair))
            if fg and bg:
                g.add((pair, SF.ratio, Literal(round(color.contrast_ratio(fg, bg), 2))))

    return g


# ============================================================
# ====================== SHAPE PER BATASAN ===================
# ============================================================


def constraint_shapes(decisions):
    """
    Menulis setiap batasan decisions.yaml sebagai satu NodeShape SHACL atas graf fakta.

    I.S. : decisions dari decisions.yaml.
    F.S. : Graf shape dikembalikan; setiap shape bernama sd-shape:<id batasan>.
    """
    g = Graph()
    g.bind("sh", SH)
    g.bind("sf", SF)
    ns = Namespace("https://scaffoldev.dev/shape#")

    def prop(shape, path, **facets):
        b = BNode()
        g.add((shape, SH.property, b))
        g.add((b, SH.path, path))
        for key, value in facets.items():
            g.add((b, SH[key], value))
        return b

    for c in decisions.get("constraints", []):
        shape = ns[c["id"]]
        g.add((shape, RDF.type, SH.NodeShape))
        g.add((shape, SH.message, Literal(f"Batasan {c['id']} ({c['kind']}) tidak terpenuhi di situs.")))
        kind = c["kind"]

        if kind == "token-equals":
            group, name = c["token"].split(".", 1)
            g.add((shape, SH.targetNode, SF[f"token--pd-{group}-{name}"]))
            prop(shape, SF.value, hasValue=Literal(normal(c["value"])), minCount=Literal(1))
        elif kind == "contrast-min":
            g.add((shape, SH.targetNode, SF[f"contrast/{c['id']}"]))
            prop(shape, SF.ratio, minInclusive=Literal(float(c.get("ratio", 4.5))), minCount=Literal(1))
        elif kind == "var-used":
            wanted = BNode()
            for path, facet, value in ((SF.selector, SH.hasValue, Literal(c["selector"])),
                                       (SF.property, SH.hasValue, Literal(c["property"])),
                                       (SF.value, SH.pattern, Literal(rf"var\(\s*{re.escape(c['var'])}\s*\)"))):
                b = BNode()
                g.add((wanted, SH.property, b))
                g.add((b, SH.path, path))
                g.add((b, facet, value))
            g.add((shape, SH.targetNode, SF.site))
            prop(shape, SF.declares, qualifiedValueShape=wanted, qualifiedMinCount=Literal(1))
        elif kind == "pattern-present":
            g.add((shape, SH.targetNode, SF[f"page/{c.get('page', 'index.html')}"]))
            prop(shape, SF.pattern, hasValue=Literal(c["pattern"]))
            g.add((shape, SH["class"], SF.Page))
        elif kind == "motion-max":
            g.add((shape, SH.targetNode, SF.site))
            if c.get("level") == "none":
                prop(shape, SF.transitions, maxInclusive=Literal(0))
        elif kind == "register":
            other = {"kamu": "anda", "Anda": "kamu"}.get(c.get("pronoun"))
            g.add((shape, SH.targetNode, SF.site))
            if other:
                prop(shape, SF[f"uses_{other}"], maxInclusive=Literal(0))

    return g


def failing_constraints(results_graph, shapes_graph):
    """
    Mengambil id batasan yang gagal dari laporan validasi pySHACL.

    I.S. : results_graph adalah graf laporan validate(); shapes_graph graf shape batasan.
    F.S. : Himpunan id batasan (nama lokal shape) dikembalikan. Hasil menunjuk property
           shape (blank node); induknya yang bernama dicari di graf shape.
    """
    failed = set()
    for result in results_graph.subjects(RDF.type, SH.ValidationResult):
        source = results_graph.value(result, SH.sourceShape)
        while source is not None and not str(source).startswith("https://scaffoldev.dev/shape#"):
            parents = list(shapes_graph.subjects(SH.property, source))
            source = parents[0] if parents else None
        if source is not None:
            failed.add(str(source).split("#", 1)[1])
    return failed


# ============================================================
# ========================== UTAMA ===========================
# ============================================================


def run(slug):
    """
    Mengekspor proyek ke RDF, memvalidasi, dan membandingkan dengan check.py.

    I.S. : Proyek sudah sampai compile_tokens; situs sudah dibangun untuk validasi batasan.
    F.S. : <work>/rdf/{model,facts,constraints}.ttl ditulis; ringkasan dikembalikan; kode 2
           bila bentuk model tidak sah atau SHACL dan check.py tidak sepakat.
    """
    proj_dir = project.open_project(slug, need=["gaps.json", "decisions.yaml", "tokens.json"])
    decisions = io.read_yaml(proj_dir / "decisions.yaml")
    out = proj_dir / "rdf"
    out.mkdir(exist_ok=True)

    model = build_model(proj_dir, slug)
    facts = build_facts(proj_dir, decisions)
    shapes = constraint_shapes(decisions)
    model.serialize(out / "model.ttl", format="turtle")
    facts.serialize(out / "facts.ttl", format="turtle")
    shapes.serialize(out / "constraints.ttl", format="turtle")

    model_ok, _, model_text = validate(model, shacl_graph=str(SHAPES), shacl_graph_format="turtle")
    _, results, _ = validate(facts, shacl_graph=shapes)
    shacl_failed = failing_constraints(results, shapes)

    constraints = decisions.get("constraints", [])
    check_findings, tfs_auto = audit_rules.evaluate_constraints(proj_dir, decisions)
    check_failed = {f["rule"].removeprefix("constraint-") for f in check_findings}
    tfs_shacl = round(1 - len(shacl_failed) / len(constraints), 2) if constraints else 1.0
    disagree = sorted(shacl_failed ^ check_failed)

    lines = [
        f"RDF ditulis ke {out} (model, facts, constraints).",
        f"  - Bentuk model terhadap tools/shapes.ttl: {'sah' if model_ok else 'TIDAK sah'}",
        f"  - TFS dari SHACL: {tfs_shacl}; TFS dari check.py: {tfs_auto}",
        f"  - Batasan gagal menurut SHACL: {', '.join(sorted(shacl_failed)) or 'tidak ada'}",
        f"  - Berbeda dengan check.py: {', '.join(disagree) or 'tidak ada'}",
    ]
    if not model_ok:
        lines += ["  " + line for line in model_text.splitlines() if "Message" in line][:10]
    if not model_ok or disagree:
        fail(EXIT_CHECK_FAILED, lines, "look at the constraints where SHACL and check.py disagree")
    return lines, "use rdf/model.ttl in tools that read RDF; nothing else to do"


def main():
    """
    Titik masuk CLI.

    I.S. : sys.argv berisi slug.
    F.S. : Hasil run() dikembalikan.
    """
    parser = argparse.ArgumentParser(description="Ekspor RDF dan validasi SHACL satu proyek.")
    parser.add_argument("slug")
    args = parser.parse_args()
    if not paths.is_valid_slug(args.slug):
        fail(EXIT_INVALID, f"Slug tidak sah: {args.slug!r}.", "use a kebab-case slug")
    return run(args.slug)


if __name__ == "__main__":
    report.run(main)
