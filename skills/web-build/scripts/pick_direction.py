# ============================================================
# File      : pick_direction.py
# Proyek    : web-skills
# Deskripsi : Memvalidasi directions.yaml, memilih satu arah visual
#             (via --pick atau sampling acak tertimbang), dan
#             menghasilkan decisions.yaml dengan batasan uji.
# ============================================================

import argparse
import itertools
import random
import secrets
import sys
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import io, paths, project, report
from lib.report import EXIT_INVALID, fail


# ============================================================
# ======================= VALIDASI ===========================
# ============================================================


def validate_directions(directions_data, brief, gaps, site_type):
    """
    Memeriksa directions.yaml terhadap skema dan aturan lintas-file.

    I.S. : directions_data dari directions.yaml; brief, gaps, dan site_type termuat.
    F.S. : List pesan galat dikembalikan (kosong bila semua aturan lolos).
    """
    errors = project.schema_errors(directions_data, "directions.schema.json")
    if errors:
        return [f"Skema directions.yaml: {err}" for err in errors]

    dirs = directions_data.get("directions", [])
    if len(dirs) != 5:
        return [f"Harus ada tepat 5 arah desain (ditemukan: {len(dirs)})."]

    # 1. Total probabilitas = 1 ± 0.01
    total_prob = sum(d.get("probability", 0) for d in dirs)
    if abs(total_prob - 1.0) > 0.01:
        errors.append(f"Probabilitas harus berjumlah 1.0 ± 0.01 (jumlah saat ini: {total_prob:.3f}).")

    styles_index = project.load_style_index()
    patterns_all = project.load_patterns()
    valid_req_ids = {r["id"] for r in gaps.get("requirements", [])}
    brief_langs = brief.get("languages", ["id"])

    sections_by_id = {s["id"]: s for s in site_type.get("sections", [])}

    for d in dirs:
        dir_id = d.get("id")
        style_id = d.get("style")
        if style_id not in styles_index:
            errors.append(f"[{dir_id}] Gaya {style_id!r} tidak terdaftar di styles/index.yaml.")
            continue

        style_file = project.load_style(style_id)
        if not style_file:
            errors.append(f"[{dir_id}] File gaya untuk {style_id!r} tidak dapat dibaca.")
            continue

        # Palet
        pal_id = d.get("palette")
        if pal_id != "custom":
            style_pals = {p["id"] for p in style_file.get("palettes", [])}
            if pal_id not in style_pals:
                errors.append(f"[{dir_id}] Palet {pal_id!r} tidak ada di gaya {style_id!r} dan bukan 'custom'.")

        # Type pairing
        pair_id = d.get("type_pairing")
        if pair_id != "custom":
            style_pairs = {p["id"] for p in style_file.get("pairings", [])}
            if pair_id not in style_pairs:
                errors.append(f"[{dir_id}] Pasangan tipografi {pair_id!r} tidak ada di gaya {style_id!r} dan bukan 'custom'.")

        # Layout
        layout_map = d.get("layout", {})
        for sec_id, pat_id in layout_map.items():
            if sec_id not in sections_by_id:
                errors.append(f"[{dir_id}] Bagian layout {sec_id!r} tidak ada di tipe situs {site_type['id']!r}.")
                continue
            kind = sections_by_id[sec_id]["pattern_kind"]
            kind_patterns = patterns_all.get(kind, {})
            if pat_id not in kind_patterns:
                errors.append(f"[{dir_id}] Pola {pat_id!r} untuk bagian {sec_id!r} tidak ada pada jenis pola {kind!r}.")

        # based_on
        for req_ref in d.get("based_on", []):
            if req_ref not in valid_req_ids:
                errors.append(f"[{dir_id}] based_on {req_ref!r} tidak ditemukan di gaps.json.")

        # register per bahasa brief
        reg_map = d.get("register", {})
        for lang in brief_langs:
            if lang not in reg_map:
                errors.append(f"[{dir_id}] register belum memiliki entri untuk bahasa {lang!r}.")

    # Perbedaan antar pasangan arah (minimal 3 dari 6 sumbu)
    for d1, d2 in itertools.combinations(dirs, 2):
        diffs = 0
        if d1.get("style") != d2.get("style"):
            diffs += 1
        if d1.get("palette") != d2.get("palette") or (d1.get("palette") == "custom" and d1.get("colors") != d2.get("colors")):
            diffs += 1
        if d1.get("type_pairing") != d2.get("type_pairing") or (d1.get("type_pairing") == "custom" and d1.get("fonts") != d2.get("fonts")):
            diffs += 1
        if d1.get("layout") != d2.get("layout"):
            diffs += 1
        if d1.get("motion") != d2.get("motion"):
            diffs += 1
        if d1.get("tone") != d2.get("tone"):
            diffs += 1

        if diffs < 3:
            errors.append(f"Arah {d1['id']} dan {d2['id']} hanya berbeda pada {diffs} sumbu (minimal 3).")

    return errors


# ============================================================
# ==================== BUILD DECISIONS =======================
# ============================================================


def build_decisions(slug, chosen, source, seed, site_type, style_data):
    """
    Menyusun struktur data decisions.yaml dari arah terpilih.

    I.S. : chosen adalah dict arah yang lolos validasi.
    F.S. : Dict decisions_data sesuai decisions.schema.json dikembalikan.
    """
    based_on = chosen["based_on"]

    # 1. d-style-1
    style_id = chosen["style"]
    border_strong = style_data["base"]["border"]["strong"]
    c_style = {
        "id": "c-style-border",
        "kind": "token-equals",
        "token": "border.strong",
        "value": border_strong,
    }
    d_style = {
        "id": "d-style-1",
        "axis": "style",
        "choice": style_id,
        "based_on": based_on,
        "rationale": chosen["rationale"]["style"],
        "source": source,
        "realized_by": ["border.strong", "shadow.hard"],
        "verified_by": ["c-style-border"],
    }

    # 2. d-palette-1
    pal_id = chosen["palette"]
    if pal_id == "custom":
        paper_val = chosen["colors"]["paper"]
    else:
        pal_entry = project.find_by_id(style_data["palettes"], pal_id)
        paper_val = pal_entry["colors"]["paper"]

    c_pal = [
        {"id": "c-palette-paper", "kind": "token-equals", "token": "color.paper", "value": paper_val},
        {"id": "c-contrast-body", "kind": "contrast-min", "fg": "color.ink", "bg": "color.paper", "ratio": 4.5},
        {"id": "c-contrast-accent", "kind": "contrast-min", "fg": "color.accent-ink", "bg": "color.accent", "ratio": 4.5},
    ]
    d_palette = {
        "id": "d-palette-1",
        "axis": "palette",
        "choice": pal_id,
        "based_on": based_on,
        "rationale": chosen["rationale"]["color"],
        "source": source,
        "realized_by": ["color.ink", "color.paper", "color.accent", "color.muted", "color.accent-ink"],
        "verified_by": [c["id"] for c in c_pal],
    }

    # 3. d-typo-1
    pair_id = chosen["type_pairing"]
    if pair_id == "custom":
        fonts = chosen["fonts"]
        typo_choice = f"custom: {fonts['display']} / {fonts['body']} / {fonts['mono']}"
    else:
        pair_entry = project.find_by_id(style_data["pairings"], pair_id)
        typo_choice = f"{pair_id}: {pair_entry['display']} / {pair_entry['body']} / {pair_entry['mono']}"

    c_typo = [
        {"id": "c-type-heading", "kind": "var-used", "selector": "h1", "property": "font-family", "var": "--pd-font-display"},
        {"id": "c-type-body", "kind": "var-used", "selector": "body", "property": "font-family", "var": "--pd-font-body"},
    ]
    d_typo = {
        "id": "d-typo-1",
        "axis": "typography",
        "choice": typo_choice,
        "based_on": based_on,
        "rationale": chosen["rationale"]["typography"],
        "source": source,
        "realized_by": ["font.display", "font.body", "font.mono"],
        "verified_by": [c["id"] for c in c_typo],
    }

    # 4. d-layout-1
    layout_map = chosen["layout"]
    sections = site_type.get("sections", [])
    layout_pairs = []
    realized_patterns = []
    c_layout = []

    for s in sections:
        sec_id = s["id"]
        pat_id = layout_map.get(sec_id)
        layout_pairs.append(f"{sec_id}={pat_id}")
        realized_patterns.append(pat_id)
        page_name = paths.page_file(s["page"])
        c_layout.append({
            "id": f"c-layout-{sec_id}",
            "kind": "pattern-present",
            "pattern": pat_id,
            "page": page_name,
        })

    layout_choice = ", ".join(layout_pairs)
    d_layout = {
        "id": "d-layout-1",
        "axis": "layout",
        "choice": layout_choice,
        "based_on": based_on,
        "rationale": chosen["rationale"]["layout"],
        "source": source,
        "realized_by": realized_patterns,
        "verified_by": [c["id"] for c in c_layout],
    }

    # 5. d-motion-1
    motion_val = chosen["motion"]
    c_motion = [{"id": "c-motion", "kind": "motion-max", "level": motion_val}]
    d_motion = {
        "id": "d-motion-1",
        "axis": "motion",
        "choice": motion_val,
        "based_on": based_on,
        "rationale": chosen["rationale"]["motion"],
        "source": source,
        "realized_by": ["motion.fast", "motion.base"],
        "verified_by": ["c-motion"],
    }

    # 6. d-tone-1
    reg_map = chosen["register"]
    reg_strs = [f"{lang}: {pronoun}" for lang, pronoun in reg_map.items()]
    tone_choice = f"{chosen['tone']} ({', '.join(reg_strs)})"
    c_reg = []
    for lang, pronoun in reg_map.items():
        c_reg.append({
            "id": f"c-register-{lang}",
            "kind": "register",
            "lang": lang,
            "pronoun": pronoun,
        })

    d_tone = {
        "id": "d-tone-1",
        "axis": "tone",
        "choice": tone_choice,
        "based_on": based_on,
        "rationale": chosen["rationale"]["tone"],
        "source": source,
        "verified_by": [c["id"] for c in c_reg],
    }

    all_constraints = (
        [c_style]
        + c_pal
        + c_typo
        + c_layout
        + c_motion
        + c_reg
    )

    return {
        "project": slug,
        "direction": chosen["id"],
        "seed": seed,
        "decisions": [d_style, d_palette, d_typo, d_layout, d_motion, d_tone],
        "constraints": all_constraints,
    }


def format_decisions_yaml(data):
    """
    Memformat data keputusan ke teks YAML blok dengan baris komentar
    dan flow map/list yang rapi sesuai konvensi.

    I.S. : data telah lolos decisions.schema.json.
    F.S. : Teks YAML dikembalikan.
    """
    src = data["decisions"][0]["source"]
    header = (
        f"# Output dari: python skills/web-build/scripts/pick_direction.py {data['project']}\n"
        f"# (sumber: {src}; seed: {data['seed']})\n"
    )
    lines = [
        header,
        f"project: {data['project']}",
        f"direction: {data['direction']}",
        f"seed: {data['seed']}",
        "decisions:",
    ]
    for d in data["decisions"]:
        lines.append(f"  - id: {d['id']}")
        lines.append(f"    axis: {d['axis']}")
        lines.append(f"    choice: {io.yaml_scalar(d['choice'])}")
        lines.append(f"    based_on: {io.yaml_flow_list(d['based_on'])}")
        lines.append(f"    rationale: {io.yaml_scalar(d['rationale'])}")
        lines.append(f"    source: {d['source']}")
        if "realized_by" in d:
            lines.append(f"    realized_by: {io.yaml_flow_list(d['realized_by'])}")
        lines.append(f"    verified_by: {io.yaml_flow_list(d['verified_by'])}")

    lines.append("constraints:")
    for c in data["constraints"]:
        lines.append(f"  - {io.yaml_flow_map(c)}")

    return "\n".join(lines) + "\n"


# ============================================================
# =========================== CLI ============================
# ============================================================


def pick(slug, pick_id=None, seed_arg=None):
    """
    Eksekusi alur pemilihan arah desain.

    I.S. : Proyek memiliki brief.yaml, gaps.json, dan directions.yaml.
    F.S. : decisions.yaml ditulis, state.yaml diperbarui, mencetak ringkasan
           dan 'NEXT: run compile_tokens.py'.
    """
    proj_dir = project.open_project(slug, need=["brief.yaml", "gaps.json", "directions.yaml"])
    brief = io.read_yaml(proj_dir / "brief.yaml")
    gaps = io.read_json(proj_dir / "gaps.json")
    directions_data = io.read_yaml(proj_dir / "directions.yaml")

    site_type = project.load_site_type(brief.get("site_type"))

    # Validasi dan cross-check
    errors = validate_directions(directions_data, brief, gaps, site_type)
    if errors:
        lines = ["Galat pada directions.yaml:"] + [f"  - {err}" for err in errors]
        fail(EXIT_INVALID, lines, "fix directions.yaml following skills/web-design/SKILL.md")

    dirs = directions_data["directions"]

    # Penentuan seed
    if seed_arg is not None:
        seed = int(seed_arg)
    else:
        seed = secrets.randbits(32)

    # Pemilihan arah
    if pick_id:
        chosen = next((d for d in dirs if d["id"] == pick_id), None)
        if not chosen:
            fail(EXIT_INVALID, f"Arah {pick_id!r} tidak ditemukan di directions.yaml.",
                 "choose an existing direction id (dir-1 to dir-5)")
        source = "client-picked"
    else:
        weights = [d["probability"] for d in dirs]
        rng = random.Random(seed)
        chosen = rng.choices(dirs, weights=weights, k=1)[0]
        source = "sampled"

    style_data = project.load_style(chosen["style"])
    decisions_data = build_decisions(slug, chosen, source, seed, site_type, style_data)

    # Validasi terhadap decisions.schema.json
    d_errors = project.schema_errors(decisions_data, "decisions.schema.json")
    if d_errors:
        fail(EXIT_INVALID, ["Hasil keputusan tidak sesuai skema:"] + d_errors,
             "check decision generation logic")

    # Tulis file
    yaml_content = format_decisions_yaml(decisions_data)
    io.write_text(proj_dir / "decisions.yaml", yaml_content)
    io.save_state(proj_dir, step="direction", seed=seed, direction=chosen["id"])

    lines = [
        f"Arah visual terpilih: {chosen['id']} ({chosen.get('summary', '')})",
        f"  - Sumber: {source} (seed: {seed})",
        f"  - Gaya: {chosen['style']}, Palet: {chosen['palette']}, Tipografi: {chosen['type_pairing']}",
        f"  - Gerak: {chosen['motion']}, Nada: {chosen['tone']}",
        f"File decisions.yaml berhasil dibuat dengan {len(decisions_data['decisions'])} keputusan dan {len(decisions_data['constraints'])} batasan.",
    ]

    return lines, "run compile_tokens.py"


def main():
    """
    Titik masuk CLI: membaca slug serta opsi --pick dan --seed dari argumen lalu menjalankan pick().

    I.S. : sys.argv berisi slug proyek dan opsi.
    F.S. : Hasil pick() dikembalikan; argparse keluar dengan kode 2 bila argumen salah.
    """
    parser = argparse.ArgumentParser(description="Pilih arah visual dan susun decisions.yaml.")
    parser.add_argument("slug", help="Slug proyek")
    parser.add_argument("--pick", help="Pilih arah tertentu (dir-1 .. dir-5)", default=None)
    parser.add_argument("--seed", type=int, help="Seed integer untuk sampling deterministik", default=None)

    args = parser.parse_args()
    return pick(args.slug, pick_id=args.pick, seed_arg=args.seed)


if __name__ == "__main__":
    report.run(main)
