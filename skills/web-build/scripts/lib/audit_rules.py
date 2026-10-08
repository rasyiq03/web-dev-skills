# ============================================================
# File      : audit_rules.py
# Proyek    : web-skills
# Deskripsi : Pemeriksa aturan konvensi kode, batasan keputusan (TFS),
#             dan audit integritas lapisan data mock.
# ============================================================

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
                    "fix": "Arahkan tautan ke halaman/seksi yang valid atau gunakan tombol <button>.",
                })

            # 2. Cek banner sebelum <section
            if "<section" in line:
                # Periksa apakah 1-4 baris sebelumnya mengandung banner
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
                    "fix": "Gunakan variabel var(--pd-color-*) yang cocok dari tokens.css.",
                })

    return findings


def check_js_conventions(site_dir):
    """
    Memeriksa JSDoc berformat I.S./F.S. pada setiap fungsi JS.

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
            # Deteksi definisi fungsi: function foo() atau const foo = () =>
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
            token_path = c.get("token", "")  # misal 'border.strong' atau 'color.paper'
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
            fg_token = c.get("fg", "")  # misal 'color.ink'
            bg_token = c.get("bg", "")
            req_ratio = c.get("ratio", 4.5)
            # Ambil nilai hex dari tokens.json
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
                # Cari blok aturan: selector_list { ... }
                # Dukung pemilih jamak seperti h1, h2, h3 { ... }
                for rule_match in re.finditer(r"([^{}]+)\{([^{}]+)\}", css_text):
                    sel_list = [s.strip() for s in rule_match.group(1).split(",")]
                    declarations = rule_match.group(2)
                    if selector in sel_list:
                        # Cari deklarasi properti di dalam blok
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
            # Jika none: tidak boleh ada transition atau animation di luar base.css
            # Jika low: transition hanya boleh di hover/focus-visible
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
            # Jika 'kamu', tidak boleh ada kata terisolasi 'Anda' di teks tampak
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

    # 1. Integritas template api
    stored_api_hashes = state.get("api_template_hashes", {})
    client_path = site_dir / "js" / "api" / "client.js"
    label_path = site_dir / "js" / "api" / "mock-label.js"
    config_path = site_dir / "js" / "api" / "config.js"

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

    # 2. Periksa endpoints.js vs mock files
    endpoints_path = site_dir / "js" / "api" / "endpoints.js"
    endpoints_map = {}
    if endpoints_path.is_file():
        text = io.read_text(endpoints_path)
        # Regex parser untuk entri: key: { method: 'GET', path: '/foo', mock: 'bar' }
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
            # Validasi skema mock
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

    # Cek pemetaan satu-ke-satu antara endpoints dan file mock
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

    # 3. Label mock pada halaman data
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
