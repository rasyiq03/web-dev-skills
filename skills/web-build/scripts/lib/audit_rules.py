# ============================================================
# File      : audit_rules.py
# Proyek    : web-skills
# Deskripsi : Pemeriksa aturan konvensi kode, batasan keputusan (TFS),
#             dan audit integritas anti-slop serta data layer.
# ============================================================

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

from lib import color, io, paths, project


# ============================================================
# ========================= KONVENSI =========================
# ============================================================


def check_file_headers(site_dir):
    """
    Memeriksa header file pada 10 baris pertama di setiap file kode site/.

    I.S. : site_dir menunjuk folder site/.
    F.S. : List finding galat dikembalikan.
    """
    findings = []
    for file_path in site_dir.rglob("*"):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(site_dir).as_posix()
        if "vendor" in rel or "data/mock" in rel or rel.endswith(".map"):
            continue
        if file_path.suffix not in (".html", ".css", ".js"):
            continue

        lines = io.read_text(file_path).splitlines()[:10]
        has_header = any("=" * 20 in line for line in lines) and any("File" in line or "Proyek" in line for line in lines)
        if not has_header:
            findings.append({
                "rule": "file-header-missing",
                "category": "lint",
                "level": "error",
                "file": f"site/{rel}",
                "line": 1,
                "message": f"Header file standar tidak ditemukan pada 10 baris pertama file {rel}.",
                "fix": "Tambahkan header file 7 baris sesuai konvensi.",
            })

    return findings


def check_html_banners_and_links(site_dir):
    """
    Memeriksa keberadaan banner sebelum setiap <section> dan mendeteksi tautan kosong (href="#").

    I.S. : site_dir folder site/.
    F.S. : List finding dikembalikan.
    """
    findings = []
    for html_file in site_dir.rglob("*.html"):
        rel = html_file.relative_to(site_dir).as_posix()
        content = io.read_text(html_file)
        lines = content.splitlines()

        for idx, line in enumerate(lines):
            # 1. Cek href="#" atau href=""
            if re.search(r'href=""|href="#"(?!\w)|href="javascript:', line):
                findings.append({
                    "rule": "empty-link",
                    "category": "design",
                    "level": "error",
                    "file": f"site/{rel}",
                    "line": idx + 1,
                    "message": "Tautan kosong atau tautan jangkar tanpa target (#) ditemukan.",
                    "fix": "Point the link at a real page, a section anchor, a tel:/mailto:/wa.me URL, or use a button.",
                })

            # 2. Cek banner sebelum <section
            if "<section" in line:
                prev_lines = lines[max(0, idx - 4):idx]
                has_banner = any("<!-- ====" in pl for pl in prev_lines)
                if not has_banner:
                    findings.append({
                        "rule": "banner-missing",
                        "category": "lint",
                        "level": "error",
                        "file": f"site/{rel}",
                        "line": idx + 1,
                        "message": "Komentar banner seksi 3 baris hilang sebelum tag <section>.",
                        "fix": "Tambahkan komentar banner 3 baris di atas tag <section>.",
                    })

    return findings


def check_css_raw_color(site_dir):
    """
    Mendeteksi warna hex mentah di luar tokens.css.

    I.S. : site_dir folder site/.
    F.S. : List finding galat raw-color dikembalikan.
    """
    findings = []
    css_dir = site_dir / "css"
    if not css_dir.is_dir():
        return findings

    for css_file in css_dir.rglob("*.css"):
        rel = css_file.relative_to(site_dir).as_posix()
        if rel.endswith("tokens.css"):
            continue

        lines = io.read_text(css_file).splitlines()
        for idx, line in enumerate(lines):
            match = re.search(r"(#[0-9A-Fa-f]{3,8}\b)", line)
            if match:
                findings.append({
                    "rule": "raw-color",
                    "category": "design",
                    "level": "error",
                    "file": f"site/{rel}",
                    "line": idx + 1,
                    "message": f"{match.group(1)} di luar tokens.css.",
                    "fix": "Use the matching var(--pd-color-*) from tokens.css.",
                })

    return findings


def check_js_conventions(site_dir):
    """
    Memeriksa JSDoc berformat I.S./F.S. pada setiap fungsi JS dan kode yang dikomentari.

    I.S. : site_dir folder site/.
    F.S. : List finding dikembalikan.
    """
    findings = []
    js_dir = site_dir / "js"
    if not js_dir.is_dir():
        return findings

    for js_file in js_dir.rglob("*.js"):
        rel = js_file.relative_to(site_dir).as_posix()
        if "vendor" in rel:
            continue

        content = io.read_text(js_file)
        lines = content.splitlines()

        for idx, line in enumerate(lines):
            func_match = re.search(r"\bfunction\s+([a-zA-Z0-9_]+)\s*\(", line)
            if func_match:
                fname = func_match.group(1)
                prev_text = "\n".join(lines[max(0, idx - 15):idx])
                if "I.S." not in prev_text or "F.S." not in prev_text:
                    findings.append({
                        "rule": "jsdoc-missing-state",
                        "category": "lint",
                        "level": "error",
                        "file": f"site/{rel}",
                        "line": idx + 1,
                        "message": f"Fungsi {fname} tidak memiliki I.S. atau F.S. pada JSDoc.",
                        "fix": "Lengkapi blok JSDoc di atas fungsi dengan baris I.S. dan F.S.",
                    })

    return findings


# ============================================================
# ========================= BATASAN ==========================
# ============================================================


def evaluate_constraints(proj_dir, decisions_data):
    """
    Mengevaluasi setiap batasan uji dalam decisions.yaml (Langkah 6).

    I.S. : proj_dir dan decisions_data valid.
    F.S. : (findings, tfs_auto) dikembalikan.
    """
    site_dir = proj_dir / "site"
    constraints = decisions_data.get("constraints", [])
    if not constraints:
        return [], 1.0

    tokens_path = proj_dir / "tokens.json"
    tokens_data = io.read_json(tokens_path) if tokens_path.is_file() else {}

    passed_count = 0
    findings = []

    for c in constraints:
        cid = c.get("id")
        kind = c.get("kind")
        passed = False
        fail_msg = ""

        if kind == "token-equals":
            token_path = c.get("token", "")
            exp_val = c.get("value")
            parts = token_path.split(".", 1)
            actual_val = None
            if len(parts) == 2 and parts[0] in tokens_data:
                actual_val = tokens_data[parts[0]].get(parts[1], {}).get("value")
            if actual_val == exp_val:
                passed = True
            else:
                fail_msg = f"Token {token_path} bernilai {actual_val!r}, diharapkan {exp_val!r}."

        elif kind == "contrast-min":
            fg_token = c.get("fg", "")
            bg_token = c.get("bg", "")
            req_ratio = c.get("ratio", 4.5)
            fg_hex = tokens_data.get("color", {}).get(fg_token.split(".")[-1], {}).get("value")
            bg_hex = tokens_data.get("color", {}).get(bg_token.split(".")[-1], {}).get("value")
            if fg_hex and bg_hex:
                ratio = color.contrast_ratio(fg_hex, bg_hex)
                if ratio >= req_ratio:
                    passed = True
                else:
                    fail_msg = f"Kontras {fg_token}/{bg_token} hanya {ratio:.2f}:1, minimal {req_ratio}:1."
            else:
                fail_msg = f"Warna untuk {fg_token} atau {bg_token} tidak ditemukan."

        elif kind == "var-used":
            selector = c.get("selector")
            prop = c.get("property")
            var_name = c.get("var")
            found_use = False
            for css_file in (site_dir / "css").rglob("*.css"):
                css_text = io.read_text(css_file)
                for rule_match in re.finditer(r"([^{}]+)\{([^{}]+)\}", css_text):
                    sel_list = [s.strip() for s in rule_match.group(1).split(",")]
                    declarations = rule_match.group(2)
                    if selector in sel_list:
                        prop_pattern = rf"\b{re.escape(prop)}\s*:\s*[^;]*var\(\s*{re.escape(var_name)}\s*\)"
                        if re.search(prop_pattern, declarations):
                            found_use = True
                            break
                if found_use:
                    break
            if found_use:
                passed = True
            else:
                fail_msg = f"Selektor {selector} belum menggunakan properti {prop}: var({var_name})."

        elif kind == "pattern-present":
            pattern_id = c.get("pattern")
            page_rel = c.get("page", "index.html")
            target_html = site_dir / page_rel
            if target_html.is_file():
                soup = BeautifulSoup(io.read_text(target_html), "html.parser")
                el = soup.find(attrs={"data-pd-pattern": pattern_id})
                if el:
                    passed = True
                else:
                    fail_msg = f"Pola layout data-pd-pattern={pattern_id!r} tidak ditemukan di {page_rel}."
            else:
                fail_msg = f"Halaman {page_rel} tidak ditemukan."

        elif kind == "motion-max":
            level = c.get("level", "medium")
            has_violation = False
            if level in ("none", "low"):
                for css_file in (site_dir / "css").rglob("*.css"):
                    if css_file.name == "base.css":
                        continue
                    text = io.read_text(css_file)
                    if level == "none" and re.search(r"\b(transition|animation)\s*:", text):
                        has_violation = True
                        break
            if not has_violation:
                passed = True
            else:
                fail_msg = f"Tingkat gerak {level!r} dilanggar oleh properti transisi/animasi CSS."

        elif kind == "register":
            lang = c.get("lang")
            pronoun = c.get("pronoun")
            target_word = "Anda" if pronoun == "kamu" else ("kamu" if pronoun == "Anda" else None)
            found_word = False
            if target_word:
                for html_file in site_dir.rglob("*.html"):
                    soup = BeautifulSoup(io.read_text(html_file), "html.parser")
                    text = soup.get_text()
                    if re.search(rf"\b{re.escape(target_word)}\b", text, re.IGNORECASE):
                        found_word = True
                        break
            if not found_word:
                passed = True
            else:
                fail_msg = f"Ditemukan kata '{target_word}' yang bertentangan dengan register {pronoun!r}."

        if passed:
            passed_count += 1
        else:
            findings.append({
                "rule": f"constraint-{cid}",
                "category": "design",
                "level": "error",
                "file": "decisions.yaml",
                "line": 1,
                "message": f"Batasan {cid} ({kind}) gagal: {fail_msg}",
                "fix": "Sesuaikan implementasi kode agar memenuhi batasan desain.",
            })

    tfs_auto = round(passed_count / len(constraints), 2)
    return findings, tfs_auto


# ============================================================
# ==================== AUDIT ANTI-SLOP =======================
# ============================================================


def _extract_all_numbers(data):
    """Mengekstrak semua angka dari struktur dict/list brief."""
    nums = set()
    if isinstance(data, dict):
        for v in data.values():
            nums.update(_extract_all_numbers(v))
    elif isinstance(data, list):
        for item in data:
            nums.update(_extract_all_numbers(item))
    elif isinstance(data, (int, float)):
        nums.add(str(data))
    elif isinstance(data, str):
        for match in re.finditer(r"\b\d+([.,]\d+)?\b", data):
            nums.add(match.group(0))
    return nums


def check_unsourced_number(proj_dir, rule, brief, decisions, site_type):
    """
    Memeriksa bahwa setiap angka pada teks tampak ada di brief.yaml atau berupa tahun/nomor telp.
    """
    findings = []
    site_dir = proj_dir / "site"
    brief_numbers = _extract_all_numbers(brief)

    for html_file in site_dir.rglob("*.html"):
        rel = html_file.relative_to(site_dir).as_posix()
        soup = BeautifulSoup(io.read_text(html_file), "html.parser")

        # Abaikan skrip, style, dan footer copyright
        for tag in soup(["script", "style"]):
            tag.decompose()

        text = soup.get_text()
        for match in re.finditer(r"\b(\d{1,10})\b", text):
            val = match.group(1)
            # Pengecualian: tahun 1900-2099
            if len(val) == 4 and (1900 <= int(val) <= 2099):
                continue
            # Pengecualian: ada di brief
            if val in brief_numbers:
                continue
            # Pengecualian: placeholder [[ISI: ...]]
            start = max(0, match.start() - 15)
            end = min(len(text), match.end() + 15)
            if "[[ISI:" in text[start:end]:
                continue

            findings.append({
                "rule": rule["id"],
                "category": "design",
                "level": rule.get("level", "error"),
                "file": f"site/{rel}",
                "line": 1,
                "message": f"Angka {val} pada teks tampak tidak ditemukan di brief.yaml.",
                "fix": rule.get("fix", "Replace the number with [[ISI: <what it measures>]] or use the value from the brief."),
            })

    return findings


def check_unsourced_quote(proj_dir, rule, brief, decisions, site_type):
    """
    Setiap <blockquote> atau blok testimonial memuat kutipan dari brief.yaml facts.
    """
    findings = []
    site_dir = proj_dir / "site"
    brief_facts_text = json.dumps(brief.get("facts", {}))

    for html_file in site_dir.rglob("*.html"):
        rel = html_file.relative_to(site_dir).as_posix()
        soup = BeautifulSoup(io.read_text(html_file), "html.parser")
        for bq in soup.find_all("blockquote"):
            quote_text = bq.get_text().strip()
            if not quote_text or "[[ISI:" in quote_text:
                continue
            if quote_text not in brief_facts_text:
                findings.append({
                    "rule": rule["id"],
                    "category": "design",
                    "level": rule.get("level", "error"),
                    "file": f"site/{rel}",
                    "line": 1,
                    "message": "Kutipan <blockquote> tidak bersumber dari facts brief.yaml.",
                    "fix": rule.get("fix", "Use a quote from the brief or [[ISI: testimoni pelanggan]]."),
                })
    return findings


def check_animate_everything(proj_dir, rule, brief, decisions, site_type):
    """
    Lebih dari 30% elemen di dalam <main> memiliki animasi / reveal.
    """
    findings = []
    site_dir = proj_dir / "site"
    for html_file in site_dir.rglob("*.html"):
        rel = html_file.relative_to(site_dir).as_posix()
        soup = BeautifulSoup(io.read_text(html_file), "html.parser")
        main_tag = soup.find("main")
        if not main_tag:
            continue
        all_els = main_tag.find_all(True)
        if not all_els:
            continue
        anim_els = [el for el in all_els if any("anim" in c or "reveal" in c or "fade" in c for c in el.get("class", []))]
        ratio = len(anim_els) / len(all_els)
        if ratio > 0.30:
            findings.append({
                "rule": rule["id"],
                "category": "design",
                "level": rule.get("level", "warning"),
                "file": f"site/{rel}",
                "line": 1,
                "message": f"{ratio * 100:.1f}% elemen di dalam <main> menggunakan animasi (>30%).",
                "fix": rule.get("fix", "Keep motion for the hero entrance and direct feedback (hover, focus, open/close)."),
            })
    return findings


def check_raw_color(proj_dir, rule, brief, decisions, site_type):
    return check_css_raw_color(proj_dir / "site")


def check_raw_font(proj_dir, rule, brief, decisions, site_type):
    findings = []
    site_dir = proj_dir / "site"
    for css_file in (site_dir / "css").rglob("*.css"):
        if css_file.name == "tokens.css":
            continue
        rel = css_file.relative_to(site_dir).as_posix()
        lines = io.read_text(css_file).splitlines()
        for idx, line in enumerate(lines):
            match = re.search(r"font-family\s*:\s*([^;]+);", line)
            if match:
                val = match.group(1).strip()
                if not val.startswith("var(--pd-font-") and val not in ("inherit", "initial", "sans-serif", "serif", "monospace"):
                    findings.append({
                        "rule": rule["id"],
                        "category": "design",
                        "level": rule.get("level", "error"),
                        "file": f"site/{rel}",
                        "line": idx + 1,
                        "message": f"Nilai font-family '{val}' di luar tokens.css.",
                        "fix": rule.get("fix", "Use var(--pd-font-display), var(--pd-font-body), or var(--pd-font-mono)."),
                    })
    return findings


def check_purple_blue_gradient(proj_dir, rule, brief, decisions, site_type):
    findings = []
    site_dir = proj_dir / "site"
    for css_file in (site_dir / "css").rglob("*.css"):
        rel = css_file.relative_to(site_dir).as_posix()
        lines = io.read_text(css_file).splitlines()
        for idx, line in enumerate(lines):
            if "gradient" in line:
                if re.search(r"(hsl\(\s*(2[2-8][0-9]|290)|#[3-9a-fA-F][0-9a-fA-F][8-9a-fA-F])", line):
                    findings.append({
                        "rule": rule["id"],
                        "category": "design",
                        "level": rule.get("level", "warning"),
                        "file": f"site/{rel}",
                        "line": idx + 1,
                        "message": "Gradien ungu-biru ditemukan di luar palet.",
                        "fix": rule.get("fix", "Use flat colors from the palette; a gradient only when the style file lists one."),
                    })
    return findings


def check_low_contrast(proj_dir, rule, brief, decisions, site_type):
    return []


def check_emoji_in_heading(proj_dir, rule, brief, decisions, site_type):
    findings = []
    site_dir = proj_dir / "site"
    emoji_pattern = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]")
    for html_file in site_dir.rglob("*.html"):
        rel = html_file.relative_to(site_dir).as_posix()
        soup = BeautifulSoup(io.read_text(html_file), "html.parser")
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "button"]):
            text = tag.get_text()
            if emoji_pattern.search(text):
                findings.append({
                    "rule": rule["id"],
                    "category": "design",
                    "level": rule.get("level", "warning"),
                    "file": f"site/{rel}",
                    "line": 1,
                    "message": f"Emoji terdeteksi pada elemen <{tag.name}>.",
                    "fix": rule.get("fix", "Use words, or an SVG icon with an accessible name."),
                })
    return findings


def check_centered_everything(proj_dir, rule, brief, decisions, site_type):
    findings = []
    site_dir = proj_dir / "site"
    for html_file in site_dir.rglob("*.html"):
        rel = html_file.relative_to(site_dir).as_posix()
        soup = BeautifulSoup(io.read_text(html_file), "html.parser")
        sections = soup.find_all("section")
        if not sections:
            continue
        centered = 0
        for s in sections:
            style = s.get("style", "")
            classes = s.get("class", [])
            if "text-align: center" in style or any("center" in c for c in classes):
                centered += 1
        ratio = centered / len(sections)
        if ratio > 0.60:
            findings.append({
                "rule": rule["id"],
                "category": "design",
                "level": rule.get("level", "warning"),
                "file": f"site/{rel}",
                "line": 1,
                "message": f"{ratio * 100:.1f}% seksi memiliki teks perataan tengah (>60%).",
                "fix": rule.get("fix", "Follow the layout pattern recorded in decisions.yaml."),
            })
    return findings


def check_pattern_missing(proj_dir, rule, brief, decisions, site_type):
    return []


def check_hardcoded_data(proj_dir, rule, brief, decisions, site_type):
    findings = []
    site_dir = proj_dir / "site"
    if brief.get("site_type") != "dashboard":
        return findings

    # Periksa dashboard HTML teks tampak (angka selain copyright)
    for html_file in site_dir.rglob("*.html"):
        rel = html_file.relative_to(site_dir).as_posix()
        soup = BeautifulSoup(io.read_text(html_file), "html.parser")
        main_tag = soup.find("main")
        if not main_tag:
            continue
        for num_match in re.finditer(r"\b\d{2,}\b", main_tag.get_text()):
            val = num_match.group(0)
            if not (1900 <= int(val) <= 2099):
                findings.append({
                    "rule": rule["id"],
                    "category": "design",
                    "level": rule.get("level", "error"),
                    "file": f"site/{rel}",
                    "line": 1,
                    "message": f"Angka data hardcoded {val} ditemukan pada halaman dashboard.",
                    "fix": rule.get("fix", "Add an endpoint in js/api/endpoints.js, put the values in data/mock/<name>.mock.json, and render them from request()."),
                })
                break
    return findings


def check_mock_file_invalid(proj_dir, rule, brief, decisions, site_type):
    return []


def check_mock_label_missing(proj_dir, rule, brief, decisions, site_type):
    return []


def check_mock_people_quotes(proj_dir, rule, brief, decisions, site_type):
    findings = []
    mock_dir = proj_dir / "site" / "data" / "mock"
    forbidden_keys = {"quote", "testimonial", "review", "testimoni", "ulasan"}
    if mock_dir.is_dir():
        for mf in mock_dir.glob("*.mock.json"):
            rel = mf.relative_to(proj_dir).as_posix()
            text = io.read_text(mf).lower()
            if any(f'"{k}"' in text for k in forbidden_keys):
                findings.append({
                    "rule": rule["id"],
                    "category": "design",
                    "level": rule.get("level", "error"),
                    "file": rel,
                    "line": 1,
                    "message": f"File mock {mf.name} memuat kunci testimoni/quote.",
                    "fix": rule.get("fix", "Remove the quotes from the mock data and use [[ISI: testimoni pelanggan]] in the page."),
                })
    return findings


def check_api_template_modified(proj_dir, rule, brief, decisions, site_type):
    return []


def check_chart_without_text(proj_dir, rule, brief, decisions, site_type):
    findings = []
    site_dir = proj_dir / "site"
    for html_file in site_dir.rglob("*.html"):
        rel = html_file.relative_to(site_dir).as_posix()
        soup = BeautifulSoup(io.read_text(html_file), "html.parser")
        for c in soup.find_all("canvas"):
            has_aria = bool(c.get("aria-label"))
            has_table = bool(c.find_next_sibling("table") or c.parent.find("table"))
            if not has_aria and not has_table:
                findings.append({
                    "rule": rule["id"],
                    "category": "design",
                    "level": rule.get("level", "error"),
                    "file": f"site/{rel}",
                    "line": 1,
                    "message": "Canvas grafik tanpa aria-label dan tanpa tabel data penyerta.",
                    "fix": rule.get("fix", "Add an aria-label summary and the same data in a visually hidden <table>."),
                })
    return findings


# ============================================================
# ==================== RUNNER ANTI-SLOP ======================
# ============================================================


def audit_anti_slop(proj_dir, brief, decisions, site_type):
    """
    Menjalankan seluruh aturan dalam audit/anti-slop.yaml.

    I.S. : proj_dir dan data terkait valid.
    F.S. : List finding temuan audit anti-slop dikembalikan.
    """
    anti_slop_path = paths.AUDIT_DIR / "anti-slop.yaml"
    if not anti_slop_path.is_file():
        return []

    data = io.read_yaml(anti_slop_path)
    rules = data.get("rules", [])
    findings = []
    site_dir = proj_dir / "site"

    for r in rules:
        rid = r["id"]

        # 1. Aturan berbasis pattern regex
        if "pattern" in r:
            pattern = re.compile(r["pattern"])
            scope = r.get("scope", "")

            target_files = []
            if "site/js/" in scope:
                js_dir = site_dir / "js"
                if js_dir.is_dir():
                    for f in js_dir.rglob("*.js"):
                        rel = f.relative_to(site_dir).as_posix()
                        if "vendor" in rel or ("client.js" in rel and "client.js" in scope):
                            continue
                        target_files.append(f)
            else:
                for ext in ("*.html", "*.css", "*.js"):
                    for f in site_dir.rglob(ext):
                        rel = f.relative_to(site_dir).as_posix()
                        if "vendor" not in rel and "data/mock" not in rel:
                            target_files.append(f)

            for tf in target_files:
                rel = tf.relative_to(site_dir).as_posix()
                content = io.read_text(tf)
                for idx, line in enumerate(content.splitlines()):
                    if pattern.search(line):
                        findings.append({
                            "rule": rid,
                            "category": "design",
                            "level": r.get("level", "error"),
                            "file": f"site/{rel}",
                            "line": idx + 1,
                            "message": f"Pola '{rid}' terdeteksi pada baris {idx + 1}.",
                            "fix": r.get("fix", "Sesuaikan kode dengan konvensi."),
                        })

        # 2. Aturan berbasis daftar sumber teks (cliche)
        elif "source" in r:
            cliche_phrases = []
            sources = r["source"] if isinstance(r["source"], list) else [r["source"]]
            for sf in sources:
                src_path = paths.AUDIT_DIR / sf
                if src_path.is_file():
                    for line in io.read_text(src_path).splitlines():
                        line_clean = line.strip().lower()
                        if line_clean and not line_clean.startswith("#"):
                            cliche_phrases.append(line_clean)

            for html_file in site_dir.rglob("*.html"):
                rel = html_file.relative_to(site_dir).as_posix()
                soup = BeautifulSoup(io.read_text(html_file), "html.parser")
                visible_text = soup.get_text().lower()
                for phrase in cliche_phrases:
                    if phrase in visible_text:
                        findings.append({
                            "rule": rid,
                            "category": "design",
                            "level": r.get("level", "warning"),
                            "file": f"site/{rel}",
                            "line": 1,
                            "message": f"Frasa klise '{phrase}' ditemukan pada teks tampak.",
                            "fix": r.get("fix", "Ganti dengan kalimat yang memuat fakta konkret dari brief."),
                        })

        # 3. Aturan berbasis fungsi cek bernama
        elif "check" in r:
            func_name = f"check_{rid.replace('-', '_')}"
            func = globals().get(func_name)
            if not func or not callable(func):
                raise ValueError(f"Fungsi pemeriksaan tidak ditemukan untuk aturan: {rid}")
            res = func(proj_dir, r, brief, decisions, site_type)
            findings.extend(res)

        else:
            raise ValueError(f"Aturan {rid} tidak memiliki pattern, source, atau check yang valid.")

    return findings


# ============================================================
# ======================== DATA LAYER ========================
# ============================================================


def check_data_layer(proj_dir, site_type):
    """
    Memeriksa integritas lapisan data mock (Langkah 7).

    I.S. : proj_dir dan site_type termuat.
    F.S. : List finding data layer dikembalikan.
    """
    findings = []
    site_dir = proj_dir / "site"
    state = io.load_state(proj_dir)

    data_sections = [s for s in site_type.get("sections", []) if s.get("data") is True]
    if not data_sections:
        return findings

    stored_api_hashes = state.get("api_template_hashes", {})
    client_path = site_dir / "js" / "api" / "client.js"
    label_path = site_dir / "js" / "api" / "mock-label.js"

    if client_path.is_file() and "client.js" in stored_api_hashes:
        if io.sha256_file(client_path) != stored_api_hashes["client.js"]:
            findings.append({
                "rule": "api-template-modified",
                "category": "design",
                "level": "error",
                "file": "site/js/api/client.js",
                "line": 1,
                "message": "File site/js/api/client.js telah diubah dari template bawaan.",
                "fix": "Pulihkan isi asli file template; letakkan perubahan hanya di endpoints.js.",
            })

    if label_path.is_file() and "mock-label.js" in stored_api_hashes:
        if io.sha256_file(label_path) != stored_api_hashes["mock-label.js"]:
            findings.append({
                "rule": "api-template-modified",
                "category": "design",
                "level": "error",
                "file": "site/js/api/mock-label.js",
                "line": 1,
                "message": "File site/js/api/mock-label.js telah diubah dari template bawaan.",
                "fix": "Pulihkan isi asli template mock-label.js.",
            })

    endpoints_path = site_dir / "js" / "api" / "endpoints.js"
    endpoints_map = {}
    if endpoints_path.is_file():
        text = io.read_text(endpoints_path)
        pattern = re.compile(r"([a-zA-Z0-9_]+)\s*:\s*\{([^}]+)\}")
        for match in pattern.finditer(text):
            ep_name = match.group(1)
            body = match.group(2)
            mock_match = re.search(r"mock\s*:\s*['\"]([^'\"]+)['\"]", body)
            if mock_match:
                endpoints_map[ep_name] = mock_match.group(1)

    mock_dir = site_dir / "data" / "mock"
    mock_files = set()
    if mock_dir.is_dir():
        for mf in mock_dir.glob("*.mock.json"):
            name = mf.name.replace(".mock.json", "")
            mock_files.add(name)
            try:
                m_data = io.read_json(mf)
                errs = project.schema_errors(m_data, "mock.schema.json")
                if errs:
                    findings.append({
                        "rule": "mock-file-invalid",
                        "category": "design",
                        "level": "error",
                        "file": f"site/data/mock/{mf.name}",
                        "line": 1,
                        "message": f"File mock {mf.name} melanggar skema: {'; '.join(errs)}",
                        "fix": "Sesuaikan file dengan schemas/mock.schema.json (butuh _mock: true dan data).",
                    })
            except Exception as e:
                findings.append({
                    "rule": "mock-file-invalid",
                    "category": "design",
                    "level": "error",
                    "file": f"site/data/mock/{mf.name}",
                    "line": 1,
                    "message": f"File mock gagal di-parse: {e}",
                    "fix": "Pastikan file berupa JSON valid.",
                })

    for ep_name, mock_name in endpoints_map.items():
        if mock_name not in mock_files:
            findings.append({
                "rule": "mock-file-invalid",
                "category": "design",
                "level": "error",
                "file": "site/js/api/endpoints.js",
                "line": 1,
                "message": f"Endpoint '{ep_name}' merujuk file mock '{mock_name}.mock.json' yang tidak ada.",
                "fix": f"Buat file site/data/mock/{mock_name}.mock.json.",
            })

    for mf_name in mock_files:
        if mf_name not in endpoints_map.values():
            findings.append({
                "rule": "mock-file-invalid",
                "category": "design",
                "level": "error",
                "file": f"site/data/mock/{mf_name}.mock.json",
                "line": 1,
                "message": f"File mock '{mf_name}.mock.json' tidak didaftarkan di endpoints.js.",
                "fix": f"Daftarkan endpoint untuk {mf_name} di site/js/api/endpoints.js.",
            })

    for s in data_sections:
        page_id = s.get("page")
        page_rel = paths.page_file(page_id)
        page_path = site_dir / page_rel
        if page_path.is_file():
            soup = BeautifulSoup(io.read_text(page_path), "html.parser")
            label_el = soup.find(attrs={"data-pd-mock-label": True})
            if not label_el:
                findings.append({
                    "rule": "mock-label-missing",
                    "category": "design",
                    "level": "error",
                    "file": f"site/{page_rel}",
                    "line": 1,
                    "message": f"Halaman data {page_rel} tidak memiliki elemen [data-pd-mock-label].",
                    "fix": "Sertakan <p class='pd-mock-label' data-pd-mock-label hidden>Data contoh</p>.",
                })

    return findings


# ============================================================
# =================== PARITAS & SIGNATURE ====================
# ============================================================


def check_bilingual_parity(proj_dir, brief):
    """
    Memeriksa paritas angka dan placeholder antara content/<lang>.yaml jika terdapat 2 bahasa.

    I.S. : proj_dir dan brief valid.
    F.S. : List finding temuan paritas dwibahasa dikembalikan.
    """
    findings = []
    langs = brief.get("languages", [])
    if len(langs) < 2:
        return findings

    c1_path = proj_dir / "content" / f"{langs[0]}.yaml"
    c2_path = proj_dir / "content" / f"{langs[1]}.yaml"

    if not c1_path.is_file() or not c2_path.is_file():
        return findings

    c1_text = io.read_text(c1_path)
    c2_text = io.read_text(c2_path)

    p1 = set(re.findall(r"\[\[ISI:\s*[^\]]+\]\]", c1_text))
    p2 = set(re.findall(r"\[\[ISI:\s*[^\]]+\]\]", c2_text))

    n1 = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", c1_text))
    n2 = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", c2_text))

    if n1 != n2:
        diff = (n1 - n2) | (n2 - n1)
        findings.append({
            "rule": "bilingual-number-mismatch",
            "category": "design",
            "level": "error",
            "file": f"content/{langs[0]}.yaml",
            "line": 1,
            "message": f"Ketidaksesuaian angka antara kedua bahasa: {', '.join(sorted(diff))}",
            "fix": "Pastikan semua angka faktual sama antara versi bahasa.",
        })

    return findings


def compute_signature_score(site_dir, decisions_data, findings):
    """
    Menghitung proporsi kepatuhan konvensi kode proyek (Signature Score).

    I.S. : site_dir dan decisions_data valid.
    F.S. : Nilai float antara 0.0 hingga 1.0 dikembalikan.
    """
    checks_total = 5
    checks_passed = 5

    # 1. Header file
    if any(f["rule"] == "file-header-missing" for f in findings):
        checks_passed -= 1

    # 2. Section banner
    if any(f["rule"] == "banner-missing" for f in findings):
        checks_passed -= 1

    # 3. Raw color di luar tokens
    if any(f["rule"] == "raw-color" for f in findings):
        checks_passed -= 1

    # 4. Tautan kosong (#)
    if any(f["rule"] == "empty-link" for f in findings):
        checks_passed -= 1

    # 5. JSDoc missing state
    if any(f["rule"] == "jsdoc-missing-state" for f in findings):
        checks_passed -= 1

    return round(max(0.0, checks_passed / checks_total), 2)
