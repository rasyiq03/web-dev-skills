# ============================================================
# File      : scaffold.py
# Proyek    : web-skills
# Deskripsi : Membuat struktur direktori site/, menyalin token & konfigurasi,
#             menyiapkan skeleton HTML per halaman, base.css, main.js,
#             dan lapisan mock API.
# ============================================================

import argparse
import shutil
import sys
from pathlib import Path

# Memungkinkan impor modul lib saat dijalankan langsung
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import io, node_tools, paths, project, report
from lib.report import EXIT_INVALID, fail


def banner_comment(title):
    """
    Membuat komentar banner 3 baris konvensi untuk HTML atau CSS.

    I.S. : title berupa string judul bagian, misal 'HERO'.
    F.S. : String 3 baris dikembalikan.
    """
    center_text = f" {title.upper()} "
    total_len = 60
    pad_len = max(2, (total_len - len(center_text)) // 2)
    left_pad = "=" * pad_len
    right_pad = "=" * (total_len - len(center_text) - pad_len)
    line2 = f"/* {left_pad}{center_text}{right_pad} */"
    line1 = f"/* {'=' * total_len} */"
    line3 = line1
    return f"{line1}\n{line2}\n{line3}"


def html_banner(title):
    """
    Membuat banner seksi dalam format komentar HTML.

    I.S. : title nama seksi.
    F.S. : String komentar HTML 3 baris dikembalikan.
    """
    banner_css = banner_comment(title)
    return banner_css.replace("/*", "<!--").replace("*/", "-->")


def file_header(file_name, project_name, description, today_str, comment_type="css"):
    """
    Menghasilkan header file standar 7 baris.

    I.S. : comment_type 'css' atau 'html'.
    F.S. : String header dikembalikan.
    """
    lines = [
        "============================================================",
        f"File      : {file_name}",
        f"Proyek    : {project_name}",
        f"Deskripsi : {description}",
        f"Dibuat    : sistem skill website {paths.VERSION}, {today_str}",
        "============================================================",
    ]
    if comment_type == "css":
        res = ["/* " + lines[0]]
        for l in lines[1:-1]:
            res.append(" * " + l)
        res.append(" * " + lines[-1] + " */\n")
        return "\n".join(res)
    else:
        res = ["<!-- " + lines[0]]
        for l in lines[1:-1]:
            res.append(" * " + l)
        res.append(" * " + lines[-1] + " -->\n")
        return "\n".join(res)


# ============================================================
# ========================= SKELETON =========================
# ============================================================


def build_base_css(project_name, today_str):
    """
    Menyusun base.css dengan reset dan aturan elemen bawaan menggunakan token.

    I.S. : project_name dan today_str diketahui.
    F.S. : String isi base.css dikembalikan.
    """
    header = file_header("base.css", project_name, "Reset dan nilai bawaan elemen", today_str, "css")
    banner_reset = banner_comment("RESET & DASAR ELEMEN")

    body = (
        f"{banner_reset}\n\n"
        "*,\n"
        "*::before,\n"
        "*::after {\n"
        "\tbox-sizing: border-box;\n"
        "\tmargin: 0;\n"
        "\tpadding: 0;\n"
        "}\n\n"
        "html {\n"
        "\tfont-size: 100%;\n"
        "}\n\n"
        "body {\n"
        "\tmin-height: 100vh;\n\n"
        "\tfont-family: var(--pd-font-body);\n"
        "\tline-height: 1.5;\n"
        "\tcolor: var(--pd-color-ink);\n\n"
        "\tbackground-color: var(--pd-color-paper);\n"
        "}\n\n"
        "h1,\n"
        "h2,\n"
        "h3 {\n"
        "\tfont-family: var(--pd-font-display);\n"
        "\tline-height: 1.2;\n"
        "\tcolor: var(--pd-color-ink);\n"
        "}\n\n"
        "a {\n"
        "\tcolor: inherit;\n"
        "}\n\n"
        ":focus-visible {\n"
        "\toutline: var(--pd-border-width) solid var(--pd-color-accent);\n"
        "\toutline-offset: var(--pd-space-xs);\n"
        "}\n"
    )
    return header + "\n" + body


def build_skeleton_html(page_id, site_type, chosen_layout, project_name, today_str, lang, fonts_links, has_data_sections, file_rel=None):
    """
    Menyusun kerangka file HTML untuk satu halaman sesuai konvensi.

    I.S. : page_id ('index', 'tentang', dll.), konfigurasi layout dan font lengkap.
    F.S. : String HTML valid dikembalikan.
    """
    if file_rel is None:
        is_root = (page_id == "index")
        file_rel = "index.html" if is_root else f"pages/{page_id}.html"

    depth = len(file_rel.split("/")) - 1
    prefix = "../" * depth
    is_root = (page_id == "index")

    # Cari section untuk halaman ini
    page_sections = [s for s in site_type.get("sections", []) if s.get("page") == page_id]

    doc_header = file_header(file_rel, project_name, f"Halaman {page_id} situs {project_name}", today_str, "html")

    lines = [
        "<!doctype html>",
        doc_header,
        f'<html lang="{lang}">',
        "<head>",
        '\t<meta charset="utf-8">',
        '\t<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'\t<meta name="generator" content="{paths.GENERATOR}">',
        f"\t<title>{project_name}</title>",
    ]

    # Link font dari fonts.html (diberi indentasi 1 tab)
    for fl in fonts_links.strip().splitlines():
        lines.append(f"\t{fl}")

    # CSS links in order: tokens, base, layout, components
    lines.append(f'\t<link rel="stylesheet" href="{prefix}css/tokens.css">')
    lines.append(f'\t<link rel="stylesheet" href="{prefix}css/base.css">')
    lines.append(f'\t<link rel="stylesheet" href="{prefix}css/layout.css">')
    lines.append(f'\t<link rel="stylesheet" href="{prefix}css/components.css">')
    lines.append("</head>")
    lines.append("<body>")

    # Header
    page_title_text = project_name if is_root else f"{project_name} — {page_id.title()}"
    mock_label_text = "Sample data" if lang == "en" else "Data contoh"

    lines.append('\t<header class="pd-header">')
    lines.append(f'\t\t<h1 class="pd-header__title">{page_title_text}</h1>')
    if has_data_sections:
        lines.append(f'\t\t<p class="pd-mock-label" data-pd-mock-label hidden>{mock_label_text}</p>')
    lines.append("\t</header>")
    lines.append("")

    # Main & sections
    lines.append('\t<main class="pd-main">')
    for s in page_sections:
        sec_id = s["id"]
        pattern_id = chosen_layout.get(sec_id, "")
        banner = html_banner(sec_id)
        for b_line in banner.splitlines():
            lines.append(f"\t\t{b_line}")
        lines.append(
            f'\t\t<section class="pd-section pd-section--{sec_id}" id="{sec_id}" data-pd-pattern="{pattern_id}"></section>'
        )
        lines.append("")

    lines.append("\t</main>")
    lines.append("")

    # Footer & script
    lines.append('\t<footer class="pd-footer"></footer>')
    lines.append(f'\t<script type="module" src="{prefix}js/main.js"></script>')
    lines.append("</body>")
    lines.append("</html>\n")

    return "\n".join(lines)


# ============================================================
# ========================= SCAFFOLD =========================
# ============================================================


def scaffold(slug, force=False):
    """
    Eksekusi scaffolding proyek projects/<slug>/.

    I.S. : projects/<slug>/ memiliki tokens.css, decisions.yaml, dan brief.yaml.
    F.S. : Folder site/ terisi lengkap, config tersalin, template mock terisi,
           state.yaml diperbarui; mencetak ringkasan dan baris NEXT.
    """
    proj_dir = project.open_project(slug, need=["brief.yaml", "decisions.yaml", "tokens.css", "fonts.html"])
    site_dir = proj_dir / "site"

    if site_dir.exists() and any(site_dir.iterdir()):
        if not force:
            fail(
                EXIT_INVALID,
                f"Folder {site_dir} sudah berisi file. Gunakan --force untuk menimpa.",
                f"run python skills/web-build/scripts/scaffold.py {slug} --force",
            )
        shutil.rmtree(site_dir)

    brief = io.read_yaml(proj_dir / "brief.yaml")
    decisions = io.read_yaml(proj_dir / "decisions.yaml")
    state = io.load_state(proj_dir)
    today_str = paths.today(state)
    project_name = brief.get("business", {}).get("name", {}).get("value", slug)
    first_lang = project.first_language(brief)

    site_type_id = brief.get("site_type")
    site_type = project.load_site_type(site_type_id)

    # Petakan layout per section dari decisions.yaml
    chosen_layout = {}
    if isinstance(decisions.get("chosen", {}).get("layout"), dict):
        chosen_layout = dict(decisions["chosen"]["layout"])
    else:
        layout_decision = next((d for d in decisions.get("decisions", []) if d.get("axis") == "layout"), {})
        for pair in layout_decision.get("choice", "").split(","):
            if "=" in pair:
                sec_k, pat_v = pair.strip().split("=", 1)
                chosen_layout[sec_k.strip()] = pat_v.strip()

    # 1. Buat folder-folder site/
    dirs_to_create = [
        site_dir / "pages",
        site_dir / "css" / "pages",
        site_dir / "js" / "components",
        site_dir / "js" / "api",
        site_dir / "js" / "vendor",
        site_dir / "data" / "mock",
        site_dir / "assets" / "img",
        site_dir / "assets" / "fonts",
    ]
    for d in dirs_to_create:
        d.mkdir(parents=True, exist_ok=True)

    # 2. Salin tokens.css
    shutil.copyfile(proj_dir / "tokens.css", site_dir / "css" / "tokens.css")

    # 3. Tulis css/base.css, css/layout.css, css/components.css
    base_css_content = build_base_css(project_name, today_str)
    io.write_text(site_dir / "css" / "base.css", base_css_content)

    layout_hdr = file_header("layout.css", project_name, "Tata letak, kontainer, dan grid seksi", today_str, "css")
    io.write_text(site_dir / "css" / "layout.css", layout_hdr)

    comp_hdr = file_header("components.css", project_name, "Komponen BEM dan kartu antarmuka", today_str, "css")
    io.write_text(site_dir / "css" / "components.css", comp_hdr)

    # 4. Mock API layer (semua proyek)
    api_template_hashes = {}
    templates_api_dir = paths.TEMPLATES_DIR / "js" / "api"
    for tmpl_file in templates_api_dir.glob("*.js"):
        content = io.read_text(tmpl_file)
        filled = (
            content.replace("{{project_name}}", project_name)
            .replace("{{version}}", paths.VERSION)
            .replace("{{date}}", today_str)
        )
        target_path = site_dir / "js" / "api" / tmpl_file.name
        io.write_text(target_path, filled)
        api_template_hashes[tmpl_file.name] = io.sha256_file(target_path)

    # 5. Cek apakah ada halaman dengan section data: true
    data_sections = [s for s in site_type.get("sections", []) if s.get("data") is True]
    has_any_data = len(data_sections) > 0

    # Tulis js/main.js
    main_hdr = file_header("main.js", project_name, "Titik masuk interaktivitas JavaScript", today_str, "css")
    main_js_body = main_hdr
    if has_any_data:
        main_js_body += "\nimport { watchMockData } from './api/mock-label.js';\n\nwatchMockData();\n"
    io.write_text(site_dir / "js" / "main.js", main_js_body)

    # 6. Khusus dashboard: charts.js, table.js, filters.js, dan chart.umd.js
    is_dashboard = (site_type_id == "dashboard")
    if is_dashboard:
        for js_name, desc in [
            ("charts.js", "Render dan konfigurasi grafik Chart.js"),
            ("table.js", "Render tabel data dan pengurutan kolom"),
            ("filters.js", "Filter data dan kontrol rentang waktu"),
        ]:
            h = file_header(js_name, project_name, desc, today_str, "css")
            io.write_text(site_dir / "js" / js_name, h)

        chart_vendor_src = paths.node_modules_dir() / "chart.js" / "dist" / "chart.umd.js"
        if chart_vendor_src.is_file():
            shutil.copyfile(chart_vendor_src, site_dir / "js" / "vendor" / "chart.umd.js")

    # 7. Skeleton HTML per halaman untuk setiap bahasa
    fonts_links = io.read_text(proj_dir / "fonts.html")
    pages_list = project.site_pages(brief, site_type)
    all_langs = brief.get("languages", ["id"])

    for l_idx, current_l in enumerate(all_langs):
        for p in pages_list:
            page_has_data = any(s.get("page") == p and s.get("data") is True for s in site_type.get("sections", []))
            if l_idx == 0:
                rel = "index.html" if p == "index" else f"pages/{p}.html"
            else:
                rel = f"{current_l}/index.html" if p == "index" else f"{current_l}/pages/{p}.html"
            target_file = site_dir / rel
            target_file.parent.mkdir(parents=True, exist_ok=True)
            html_code = build_skeleton_html(
                p, site_type, chosen_layout, project_name, today_str, current_l, fonts_links, page_has_data, file_rel=rel
            )
            io.write_text(target_file, html_code)

    # 8. Salin konfigurasi dari config/ ke projects/<slug>/ dan hash
    config_hashes = {}
    for cfg_file in paths.CONFIG_DIR.iterdir():
        if cfg_file.is_file():
            dest = proj_dir / cfg_file.name
            shutil.copyfile(cfg_file, dest)
            config_hashes[cfg_file.name] = io.sha256_file(dest)

    # 9. Format awal dengan Prettier agar skeleton langsung lolos prettier --check
    #    (kegagalan Prettier dilaporkan check.py sebagai tool-failed)
    node_tools.run_tool("prettier", ["--write", "site/**/*.{html,css}"], proj_dir)

    io.save_state(
        proj_dir,
        step="scaffold",
        config_hashes=config_hashes,
        api_template_hashes=api_template_hashes,
    )

    lines = [
        f"Scaffolding berhasil untuk '{slug}':",
        f"  - site/ ({len(pages_list)} halaman HTML: {', '.join(pages_list)})",
        "  - css/ (tokens.css, base.css, layout.css, components.css)",
        "  - js/ (main.js, mock API layer di js/api/)",
        f"  - {len(config_hashes)} file konfigurasi disalin dan di-hash",
    ]
    if is_dashboard:
        lines.append("  - File khusus dashboard (charts.js, table.js, filters.js, chart.umd.js) disiapkan")

    return lines, f"write content/{first_lang}.yaml (web-build skill step 5)"


def main():
    """
    Titik masuk CLI: membaca slug dan opsi --force dari argumen lalu menjalankan scaffold().

    I.S. : sys.argv berisi slug proyek dan opsi.
    F.S. : Hasil scaffold() dikembalikan; argparse keluar dengan kode 2 bila argumen salah.
    """
    parser = argparse.ArgumentParser(description="Buat kerangka proyek web-build.")
    parser.add_argument("slug", help="Slug proyek")
    parser.add_argument("--force", action="store_true", help="Timpa isi site/ jika sudah ada")

    args = parser.parse_args()
    return scaffold(args.slug, force=args.force)


if __name__ == "__main__":
    report.run(main)
