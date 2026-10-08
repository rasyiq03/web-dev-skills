# ============================================================
# File      : serve.py
# Proyek    : web-skills
# Deskripsi : Server HTTP interaktif untuk kuesioner brief.
#             Menggunakan standard library saja dengan token acak
#             dan perlindungan Host header.
# ============================================================

import argparse
import http.server
import json
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path

# Impor pustaka internal proyek
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib import io, paths, project


# ============================================================
# ====================== PEMBANTU DATA =======================
# ============================================================


def set_nested_value(data, key_path, value):
    """
    Menetapkan nilai bersarang dalam dictionary berdasarkan path bertitik.

    I.S. : data berupa dict, key_path string misal 'business.differentiator'.
    F.S. : Node target diperbarui dengan {'value': value, 'source': 'stated', 'note': 'form'}.
    """
    parts = key_path.split(".")
    curr = data
    for p in parts[:-1]:
        if p not in curr or not isinstance(curr[p], dict):
            curr[p] = {}
        curr = curr[p]

    curr[parts[-1]] = {
        "value": value,
        "source": "stated",
        "note": "form",
    }


def build_form_html(slug, lang, questions, token):
    """
    Menghasilkan halaman formulir HTML sesuai konvensi pd-.

    I.S. : slug nama proyek, lang kode bahasa, questions daftar pertanyaan, token token akses.
    F.S. : String dokumen HTML lengkap dikembalikan.
    """
    is_id = lang == "id"
    title = f"Kuesioner Brief — {slug}" if is_id else f"Brief Questionnaire — {slug}"
    submit_label = "Kirim Jawaban" if is_id else "Submit Answers"
    desc_text = (
        "Lengkapi informasi proyek berikut untuk melanjutkan pembuatan situs."
        if is_id
        else "Fill in the project details below to continue building the site."
    )

    questions_html = []
    for q in questions:
        field = q.get("field", "")
        ask_dict = q.get("ask", {})
        label_text = ask_dict.get(lang) or ask_dict.get("id") or ask_dict.get("en") or field

        field_html = f"""\t\t\t\t<div class="pd-form-group">
\t\t\t\t\t<label class="pd-label" for="{field}">{label_text}</label>
\t\t\t\t\t<input class="pd-input" id="{field}" name="{field}" type="text" placeholder="{label_text}">
\t\t\t\t</div>"""
        questions_html.append(field_html)

    fields_rendered = "\n".join(questions_html)

    return f"""<!doctype html>
<!-- ============================================================ -->
<!-- File      : form.html                                        -->
<!-- Proyek    : {slug}                                           -->
<!-- Deskripsi : Formulir pengisian rincian brief interaktif       -->
<!-- ============================================================ -->
<html lang="{lang}">
<head>
\t<meta charset="utf-8">
\t<meta name="viewport" content="width=device-width, initial-scale=1.0">
\t<title>{title}</title>
\t<style>
\t\t:root {{
\t\t\t--pd-color-ink: #111111;
\t\t\t--pd-color-paper: #F7F7F7;
\t\t\t--pd-color-accent: #2B4C7E;
\t\t\t--pd-color-accent-ink: #FFFFFF;
\t\t\t--pd-font-body: system-ui, -apple-system, sans-serif;
\t\t}}
\t\tbody {{
\t\t\tmargin: 0;
\t\t\tpadding: 2rem;
\t\t\tbackground: var(--pd-color-paper);
\t\t\tcolor: var(--pd-color-ink);
\t\t\tfont-family: var(--pd-font-body);
\t\t\tline-height: 1.5;
\t\t}}
\t\t.pd-container {{
\t\t\tmax-width: 640px;
\t\t\tmargin: 0 auto;
\t\t\tbackground: #FFFFFF;
\t\t\tpadding: 2rem;
\t\t\tborder-radius: 8px;
\t\t\tbox-shadow: 0 2px 8px rgba(0,0,0,0.06);
\t\t}}
\t\t.pd-form-group {{
\t\t\tmargin-bottom: 1.25rem;
\t\t}}
\t\t.pd-label {{
\t\t\tdisplay: block;
\t\t\tfont-weight: 600;
\t\t\tmargin-bottom: 0.35rem;
\t\t}}
\t\t.pd-input {{
\t\t\twidth: 100%;
\t\t\tbox-sizing: border-box;
\t\t\tpadding: 0.6rem 0.75rem;
\t\t\tborder: 1px solid #CCC;
\t\t\tborder-radius: 4px;
\t\t\tfont-size: 1rem;
\t\t}}
\t\t.pd-btn {{
\t\t\tbackground: var(--pd-color-accent);
\t\t\tcolor: var(--pd-color-accent-ink);
\t\t\tborder: none;
\t\t\tpadding: 0.75rem 1.5rem;
\t\t\tfont-size: 1rem;
\t\t\tfont-weight: 600;
\t\t\tborder-radius: 4px;
\t\t\tcursor: pointer;
\t\t}}
\t\t.pd-message {{
\t\t\tmargin-top: 1rem;
\t\t\tfont-weight: 600;
\t\t}}
\t</style>
</head>
<body>
\t<!-- ============================================================ -->
\t<!-- Section: Kuesioner Interaktif                                 -->
\t<!-- ============================================================ -->
\t<main class="pd-container">
\t\t<h1>{title}</h1>
\t\t<p>{desc_text}</p>
\t\t<form id="brief-form">
{fields_rendered}
\t\t\t<button class="pd-btn" type="submit">{submit_label}</button>
\t\t</form>
\t\t<div class="pd-message" id="msg"></div>
\t</main>
\t<script>
\t\tdocument.getElementById("brief-form").addEventListener("submit", async function(e) {{
\t\t\te.preventDefault();
\t\t\tconst formData = new FormData(this);
\t\t\tconst answers = {{}};
\t\t\tfor (const [key, value] of formData.entries()) {{
\t\t\t\tif (value.trim() !== "") {{
\t\t\t\t\tanswers[key] = value.trim();
\t\t\t\t}}
\t\t\t}}
\t\t\ttry {{
\t\t\t\tconst res = await fetch("/" + "{token}" + "/submit", {{
\t\t\t\t\tmethod: "POST",
\t\t\t\t\theaders: {{ "Content-Type": "application/json" }},
\t\t\t\t\tbody: JSON.stringify(answers)
\t\t\t\t}});
\t\t\t\tif (res.ok) {{
\t\t\t\t\tdocument.getElementById("msg").textContent = "Jawaban berhasil disimpan. Anda dapat menutup tab ini.";
\t\t\t\t\tdocument.getElementById("brief-form").style.display = "none";
\t\t\t\t}} else {{
\t\t\t\t\tdocument.getElementById("msg").textContent = "Gagal menyimpan jawaban: " + res.status;
\t\t\t\t}}
\t\t\t}} catch (err) {{
\t\t\t\tdocument.getElementById("msg").textContent = "Kesalahan koneksi: " + err.message;
\t\t\t}}
\t\t}});
\t</script>
</body>
</html>
"""


# ============================================================
# ===================== HTTP HANDLER =========================
# ============================================================


class QuestionnaireHandler(http.server.BaseHTTPRequestHandler):
    """
    Handler HTTP khusus untuk server kuesioner brief.
    """

    def log_message(self, format, *args):
        # Mencegah polusi stdout dengan log server standar
        pass

    def validate_host(self):
        """
        Memastikan host header hanya 127.0.0.1:<port> atau localhost:<port>.
        """
        host = self.headers.get("Host", "")
        allowed = [
            f"127.0.0.1:{self.server.port}",
            f"localhost:{self.server.port}",
        ]
        return host in allowed

    def do_GET(self):
        # 1. Validasi Host
        if not self.validate_host():
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden: invalid Host header\n")
            return

        # 2. Validasi Path Token
        expected_path = f"/{self.server.token}/"
        alt_path = f"/{self.server.token}"
        clean_path = self.path.split("?")[0]
        if clean_path != expected_path and clean_path != alt_path:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found\n")
            return

        # 3. Sajikan Form HTML
        html_bytes = self.server.form_html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_bytes)))
        self.end_headers()
        self.wfile.write(html_bytes)

    def do_POST(self):
        # 1. Validasi Host
        if not self.validate_host():
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden: invalid Host header\n")
            return

        # 2. Validasi Path Submit
        expected_submit = f"/{self.server.token}/submit"
        clean_path = self.path.split("?")[0]
        if clean_path != expected_submit:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found\n")
            return

        # 3. Validasi Content-Type
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Bad Request: Content-Type must be application/json\n")
            return

        # 4. Validasi Submission Tunggal (Second submission -> 409)
        with self.server.lock:
            if self.server.submitted:
                self.send_response(409)
                self.end_headers()
                self.wfile.write(b"Conflict: form already submitted\n")
                return

        # 5. Baca Payload
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            answers = json.loads(body_bytes.decode("utf-8"))
        except Exception as e:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Bad Request: {e}\n".encode("utf-8"))
            return

        # 6. Simpan Jawaban
        with self.server.lock:
            self.server.submitted = True
            self.server.received_answers = answers

        resp_body = b'{"status": "ok", "message": "ANSWERS SAVED"}\n'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_body)))
        self.end_headers()
        self.wfile.write(resp_body)


# ============================================================
# ==================== LOGIKA UTAMA ==========================
# ============================================================


def run_server(slug, timeout_seconds=1800):
    """
    Menjalankan server kuesioner brief interaktif hingga jawaban diterima atau timeout.

    I.S. : slug nama proyek, timeout_seconds batas waktu server berjalan.
    F.S. : Exit 0 bila tersimpan, exit 4 bila waktu habis, exit 1 bila input tidak valid.
    """
    proj_dir = paths.project_dir(slug)
    if not proj_dir.is_dir():
        print(f"Error: direktori proyek 'projects/{slug}' tidak ditemukan.", file=sys.stderr)
        sys.exit(1)

    brief_file = proj_dir / "brief.yaml"
    if not brief_file.is_file():
        print(f"Error: 'brief.yaml' tidak ditemukan di 'projects/{slug}'.", file=sys.stderr)
        sys.exit(1)

    brief = io.read_yaml(brief_file)
    langs = brief.get("languages", ["id"])
    lang = langs[0] if langs else "id"

    # Muat pertanyaan dari gaps.json
    gaps_file = proj_dir / "gaps.json"
    if gaps_file.is_file():
        gaps_data = io.read_json(gaps_file)
        questions = gaps_data.get("questions", [])
    else:
        # Fallback jika gaps.json belum ada: baca dari site-type
        st_id = brief.get("site_type", "company-profile")
        st_file = paths.site_type_file(st_id)
        st_data = io.read_yaml(st_file) if st_file.is_file() else {}
        questions = st_data.get("questions", [])

    token = secrets.token_urlsafe(16)
    form_html = build_form_html(slug, lang, questions, token)

    # Bind pada 127.0.0.1:0 (port acak yang tersedia)
    server = http.server.HTTPServer(("127.0.0.1", 0), QuestionnaireHandler)
    port = server.server_port

    server.port = port
    server.token = token
    server.form_html = form_html
    server.submitted = False
    server.received_answers = None
    server.lock = threading.Lock()

    # Cetak URL segera dan flush stdout
    url = f"http://127.0.0.1:{port}/{token}/"
    print(f"URL: {url}")
    sys.stdout.flush()

    # Jalankan server dalam thread terpisah
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    start_time = time.time()
    while True:
        with server.lock:
            if server.submitted:
                break

        if time.time() - start_time >= timeout_seconds:
            server.shutdown()
            print(f"Batas waktu interaksi ({timeout_seconds}s) terlampaui.")
            print("NEXT: continue without answers")
            sys.exit(4)

        time.sleep(0.1)

    # Beri jeda singkat agar respon pertama selesai dan submit kedua (bila ada) menerima 409
    time.sleep(0.3)
    server.shutdown()

    # Simpan jawaban ke brief.yaml
    answers = server.received_answers or {}
    if answers:
        for k, v in answers.items():
            set_nested_value(brief, k, v)
        io.write_yaml(brief_file, brief)

    # Validasi ulang brief
    val_script = paths.scripts_dir() / "validate_brief.py"
    subprocess.run([sys.executable, str(val_script), slug], check=False)

    print("ANSWERS SAVED")
    print("NEXT: run gaps.py")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Jalankan server kuesioner brief interaktif.")
    parser.add_argument("slug", help="Slug proyek")
    parser.add_argument("--timeout", type=int, default=1800, help="Batas waktu server (detik)")
    args = parser.parse_args()

    run_server(args.slug, args.timeout)


if __name__ == "__main__":
    main()
