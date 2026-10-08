# ============================================================
# File      : compile_tokens.py
# Proyek    : web-skills
# Deskripsi : Mengompilasi keputusan desain menjadi tokens.json (DTCG),
#             tokens.css (variabel CSS), dan fonts.html (Google Fonts).
#             Memeriksa kepatuhan kontras WCAG 2.x (>= 4.5:1).
# ============================================================

import sys
import urllib.parse
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import color, io, paths, project, report
from lib.report import EXIT_CHECK_FAILED, EXIT_INVALID, fail

SERIF_FONTS = {
    "fraunces", "newsreader", "instrument serif", "playfair display", "merriweather",
    "lora", "pt serif", "eb garamond", "cormorant", "libre baskerville", "serif"
}


def is_serif(font_name):
    """
    Menentukan apakah suatu nama font termasuk kelompok serif.

    I.S. : font_name nama keluarga font, misal 'Newsreader'.
    F.S. : True bila serif, False bila sans-serif.
    """
    name_lower = font_name.lower().strip()
    return any(s in name_lower for s in SERIF_FONTS)


# ============================================================
# ========================= KOMPILASI ========================
# ============================================================


def compile_tokens(slug):
    """
    Menghasilkan tokens.json, tokens.css, dan fonts.html untuk proyek.

    I.S. : projects/<slug>/ memiliki brief.yaml, directions.yaml, dan decisions.yaml.
    F.S. : Tiga file token tertulis di folder proyek; state.yaml diperbarui;
           mencetak ringkasan dan 'NEXT: run scaffold.py'.
    """
    proj_dir = project.open_project(slug, need=["brief.yaml", "directions.yaml", "decisions.yaml"])
    brief = io.read_yaml(proj_dir / "brief.yaml")
    decisions = io.read_yaml(proj_dir / "decisions.yaml")
    directions_data = io.read_yaml(proj_dir / "directions.yaml")

    chosen_dir_id = decisions.get("direction")
    chosen = next((d for d in directions_data.get("directions", []) if d["id"] == chosen_dir_id), None)
    if not chosen:
        fail(EXIT_INVALID, f"Arah {chosen_dir_id!r} dari decisions.yaml tidak ditemukan di directions.yaml.",
             "check direction id in decisions.yaml")

    style_id = chosen["style"]
    style_data = project.load_style(style_id)
    if not style_data:
        fail(EXIT_INVALID, f"File gaya {style_id!r} tidak ditemukan.", "check style id in decisions.yaml")

    base = style_data.get("base", {})

    # 1. Warna palet
    pal_id = chosen["palette"]
    if pal_id == "custom":
        raw_colors = chosen.get("colors", {})
    else:
        pal_entry = project.find_by_id(style_data.get("palettes", []), pal_id)
        if not pal_entry:
            fail(EXIT_INVALID, f"Palet {pal_id!r} tidak ada di gaya {style_id!r}.", "fix palette in directions.yaml")
        raw_colors = pal_entry["colors"]

    ink = raw_colors["ink"]
    paper = raw_colors["paper"]
    accent = raw_colors["accent"]
    muted = raw_colors["muted"]
    accent_ink = raw_colors["accent-ink"]

    # 2. Uji kontras WCAG 2.x (harus >= 4.5:1)
    ratio_ink_paper = color.contrast_ratio(ink, paper)
    if ratio_ink_paper < 4.5:
        fail(
            EXIT_CHECK_FAILED,
            f"Kontras teks utama tidak memenuhi syarat WCAG AA: ink ({ink}) / paper ({paper}) = {ratio_ink_paper:.2f}:1 (minimal 4.5:1).",
            "adjust palette colors to achieve at least 4.5:1 contrast",
        )

    ratio_muted_paper = color.contrast_ratio(muted, paper)
    if ratio_muted_paper < 4.5:
        fail(
            EXIT_CHECK_FAILED,
            f"Kontras teks sekunder tidak memenuhi syarat WCAG AA: muted ({muted}) / paper ({paper}) = {ratio_muted_paper:.2f}:1 (minimal 4.5:1).",
            "adjust palette colors to achieve at least 4.5:1 contrast",
        )

    ratio_accent_ink = color.contrast_ratio(accent_ink, accent)
    if ratio_accent_ink < 4.5:
        fail(
            EXIT_CHECK_FAILED,
            f"Kontras tombol/aksen tidak memenuhi syarat WCAG AA: accent-ink ({accent_ink}) / accent ({accent}) = {ratio_accent_ink:.2f}:1 (minimal 4.5:1).",
            "adjust palette colors to achieve at least 4.5:1 contrast",
        )

    # 3. Warna turunan grafik dan status (OKLCH)
    chart_colors = {
        "chart-1": accent,
        "chart-2": color.derive_chart_color(accent, paper, 60),
        "chart-3": color.derive_chart_color(accent, paper, 120),
        "chart-4": color.derive_chart_color(accent, paper, 180),
        "chart-5": color.derive_chart_color(accent, paper, 240),
        "chart-6": color.derive_chart_color(accent, paper, 300),
    }

    state_colors = {
        "positive": color.derive_state_color(145, paper),
        "negative": color.derive_state_color(25, paper),
        "warning": color.derive_state_color(80, paper),
    }

    all_colors = {
        "ink": ink,
        "paper": paper,
        "accent": accent,
        "muted": muted,
        "accent-ink": accent_ink,
        **chart_colors,
        **state_colors,
    }

    # 4. Tipografi
    pair_id = chosen["type_pairing"]
    if pair_id == "custom":
        raw_fonts = chosen.get("fonts", {})
    else:
        pair_entry = project.find_by_id(style_data.get("pairings", []), pair_id)
        if not pair_entry:
            fail(EXIT_INVALID, f"Pasangan font {pair_id!r} tidak ada di gaya {style_id!r}.", "fix font pairing in directions.yaml")
        raw_fonts = {
            "display": pair_entry["display"],
            "body": pair_entry["body"],
            "mono": pair_entry["mono"],
        }

    disp_family = raw_fonts["display"]
    body_family = raw_fonts["body"]
    mono_family = raw_fonts["mono"]

    disp_fallback = "serif" if is_serif(disp_family) else "sans-serif"
    body_fallback = "serif" if is_serif(body_family) else "sans-serif"
    mono_fallback = "monospace"

    fonts_tokens = {
        "display": f"'{disp_family}', {disp_fallback}",
        "body": f"'{body_family}', {body_fallback}",
        "mono": f"'{mono_family}', {mono_fallback}",
    }

    # 5. Skala ukuran (type_scale: base, ratio)
    type_scale = base.get("type_scale", {"base": "1rem", "ratio": 1.25})
    base_rem_val = float(str(type_scale["base"]).replace("rem", "").strip())
    ratio_val = float(type_scale["ratio"])

    size_tokens = {}
    for n in range(-2, 6):
        step_val = base_rem_val * (ratio_val ** n)
        val_str = f"{step_val:.3f}rem"
        # Sertakan format Utopia/DTCG
        size_tokens[f"step-{n}"] = val_str

    # 6. Ruang, Radius, Border, Shadow, Motion
    space_tokens = {k: str(v) for k, v in base.get("space", {}).items()}
    radius_tokens = {k: str(v) for k, v in base.get("radius", {}).items()}
    border_tokens = {k: str(v) for k, v in base.get("border", {}).items()}
    shadow_tokens = {k: str(v) for k, v in base.get("shadow", {}).items()}
    motion_tokens = {k: str(v) for k, v in base.get("motion", {}).items()}

    # Susun tokens.json (DTCG)
    def dtcg_group(token_dict, token_type):
        """
        Membungkus pasangan nama-nilai token menjadi satu grup DTCG.

        I.S. : token_dict berisi nama token -> nilai string; token_type adalah $type DTCG.
        F.S. : Dict {nama: {$value, $type, value}} dikembalikan.
        """
        return {
            k: {"$value": v, "$type": token_type, "value": v}
            for k, v in token_dict.items()
        }

    tokens_json_data = {
        "$schema": "https://design-tokens.github.io/community-group/format/",
        "color": dtcg_group(all_colors, "color"),
        "font": dtcg_group(fonts_tokens, "fontFamily"),
        "size": dtcg_group(size_tokens, "dimension"),
        "space": dtcg_group(space_tokens, "dimension"),
        "radius": dtcg_group(radius_tokens, "dimension"),
        "border": dtcg_group(border_tokens, "border"),
        "shadow": dtcg_group(shadow_tokens, "shadow"),
        "motion": dtcg_group(motion_tokens, "duration"),
    }
    io.write_json(proj_dir / "tokens.json", tokens_json_data)

    # 7. Susun tokens.css
    state = io.load_state(proj_dir)
    today_str = paths.today(state)
    project_name = brief.get("business", {}).get("name", {}).get("value", slug)

    css_lines = [
        "/* ============================================================",
        " * File      : tokens.css",
        f" * Proyek    : {project_name}",
        " * Deskripsi : Variabel desain sistem (token). Dibuat otomatis,",
        " *             jangan diedit manual.",
        f" * Dibuat    : sistem skill website {paths.VERSION}, {today_str}",
        " * ============================================================ */",
        "",
        ":root {",
        "\t/* ============================================================ */",
        "\t/* =========================== WARNA ========================== */",
        "\t/* ============================================================ */",
    ]

    for k, v in all_colors.items():
        css_lines.append(f"\t--pd-color-{k}: {v};")

    css_lines += [
        "",
        "\t/* ============================================================ */",
        "\t/* ========================= TIPOGRAFI ======================== */",
        "\t/* ============================================================ */",
    ]
    for k, v in fonts_tokens.items():
        css_lines.append(f"\t--pd-font-{k}: {v};")

    css_lines += [
        "",
        "\t/* ============================================================ */",
        "\t/* ========================== UKURAN ========================== */",
        "\t/* ============================================================ */",
    ]
    for n in range(-2, 6):
        val_str = size_tokens[f"step-{n}"]
        if n < 0:
            css_name = f"step-neg-{abs(n)}"
        else:
            css_name = f"step-{n}"
        css_lines.append(f"\t--pd-size-{css_name}: {val_str};")

    css_lines += [
        "",
        "\t/* ============================================================ */",
        "\t/* =========================== RUANG ========================== */",
        "\t/* ============================================================ */",
    ]
    for k, v in space_tokens.items():
        css_lines.append(f"\t--pd-space-{k}: {v};")

    css_lines += [
        "",
        "\t/* ============================================================ */",
        "\t/* ========================== RADIUS ========================== */",
        "\t/* ============================================================ */",
    ]
    for k, v in radius_tokens.items():
        css_lines.append(f"\t--pd-radius-{k}: {v};")

    css_lines += [
        "",
        "\t/* ============================================================ */",
        "\t/* =========================== BORDER ========================= */",
        "\t/* ============================================================ */",
    ]
    for k, v in border_tokens.items():
        css_lines.append(f"\t--pd-border-{k}: {v};")

    css_lines += [
        "",
        "\t/* ============================================================ */",
        "\t/* ========================== BAYANGAN ======================== */",
        "\t/* ============================================================ */",
    ]
    for k, v in shadow_tokens.items():
        css_lines.append(f"\t--pd-shadow-{k}: {v};")

    css_lines += [
        "",
        "\t/* ============================================================ */",
        "\t/* =========================== GERAK ========================== */",
        "\t/* ============================================================ */",
    ]
    for k, v in motion_tokens.items():
        css_lines.append(f"\t--pd-motion-{k}: {v};")

    css_lines.append("}\n")

    tokens_css_content = "\n".join(css_lines)
    io.write_text(proj_dir / "tokens.css", tokens_css_content)

    # 8. Susun fonts.html
    # Bangun parameter URL Google Fonts
    font_params = []
    for fam in [disp_family, body_family, mono_family]:
        safe_name = fam.replace(" ", "+")
        font_params.append(f"family={safe_name}:wght@400;600;700")

    query_str = "&".join(font_params) + "&display=swap"
    google_fonts_url = f"https://fonts.googleapis.com/css2?{query_str}"

    fonts_html_content = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link rel="stylesheet" href="{google_fonts_url}">\n'
    )
    io.write_text(proj_dir / "fonts.html", fonts_html_content)

    io.save_state(proj_dir, step="tokens")

    lines = [
        f"Kompilasi token berhasil untuk '{slug}':",
        f"  - tokens.json ({len(tokens_json_data)} grup DTCG)",
        f"  - tokens.css (variabel CSS :root dengan banner konvensi)",
        f"  - fonts.html (Google Fonts: {disp_family}, {body_family}, {mono_family})",
        f"  - Kontras: ink/paper {ratio_ink_paper:.2f}:1, muted/paper {ratio_muted_paper:.2f}:1, accent-ink/accent {ratio_accent_ink:.2f}:1",
    ]

    return lines, "run scaffold.py"


def main():
    """
    Titik masuk CLI: membaca slug dari argumen lalu menjalankan compile_tokens().

    I.S. : sys.argv berisi slug proyek, atau kosong.
    F.S. : Hasil compile_tokens() dikembalikan; keluar dengan kode 1 bila slug tidak diberikan.
    """
    if len(sys.argv) < 2:
        fail(EXIT_INVALID, "Penggunaan: python compile_tokens.py <slug>", "specify a project slug")
    return compile_tokens(sys.argv[1])


if __name__ == "__main__":
    report.run(main)
