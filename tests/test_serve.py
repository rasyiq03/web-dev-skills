# ============================================================
# File      : test_serve.py
# Deskripsi : Pengujian fungsionalitas serve.py:
#             - Token salah -> 404
#             - Host header salah -> 403
#             - Submit ganda -> 409
#             - Timeout tercapai -> exit 4
#             - Submit berhasil -> perbarui brief.yaml & exit 0
# ============================================================

import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from conftest import copy_fixture
from lib import io, paths


def start_serve_process(slug, timeout=10):
    """
    Menjalankan proses serve.py dan membaca URL yang dihasilkan.

    I.S. : slug nama proyek, timeout batas waktu server dalam detik.
    F.S. : Tuple (proc, url, token, port) dikembalikan.
    """
    proc = subprocess.Popen(
        [
            sys.executable,
            str(paths.scripts_dir() / "serve.py"),
            slug,
            "--timeout",
            str(timeout),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(paths.repo_root()),
    )

    # Baca baris pertama untuk mengambil URL
    url_line = proc.stdout.readline()
    match = re.search(r"URL:\s*(http://127\.0\.0\.1:(\d+)/([^/]+)/)", url_line)
    assert match, f"URL tidak ditemukan pada output: {url_line}"

    url = match.group(1)
    port = int(match.group(2))
    token = match.group(3)

    return proc, url, token, port


def test_serve_timeout(projects_dir):
    """
    Memverifikasi bahwa jika tidak ada submission hingga batas timeout (--timeout 2),
    serve.py mencetak 'NEXT: continue without answers' dan keluar dengan kode 4.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml"])
    proc, url, token, port = start_serve_process("kopi-senja", timeout=2)

    # Tunggu proses selesai karena timeout
    stdout, stderr = proc.communicate(timeout=6)
    assert proc.returncode == 4
    assert "NEXT: continue without answers" in stdout


def test_serve_security_and_errors(projects_dir):
    """
    Memverifikasi penanganan keamanan:
    - Path tanpa token / token salah -> 404
    - Host header bukan 127.0.0.1:<port> atau localhost:<port> -> 403
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml"])
    proc, url, token, port = start_serve_process("kopi-senja", timeout=10)

    try:
        # 1. Token salah -> 404
        bad_token_url = f"http://127.0.0.1:{port}/invalid-token/"
        req_bad_token = urllib.request.Request(bad_token_url)
        try:
            urllib.request.urlopen(req_bad_token)
            assert False, "Harusnya menghasilkan 404"
        except urllib.error.HTTPError as e:
            assert e.code == 404

        # 2. Host header salah -> 403
        req_bad_host = urllib.request.Request(url, headers={"Host": "malicious-site.com"})
        try:
            urllib.request.urlopen(req_bad_host)
            assert False, "Harusnya menghasilkan 403"
        except urllib.error.HTTPError as e:
            assert e.code == 403

        # 3. GET dengan token valid -> 200 HTML form
        resp = urllib.request.urlopen(url)
        assert resp.status == 200
        html = resp.read().decode("utf-8")
        assert "Kuesioner Brief" in html
        assert "<form id=\"brief-form\">" in html

    finally:
        proc.kill()
        proc.wait()


def test_serve_successful_submit_and_double_submit(projects_dir):
    """
    Memverifikasi submission jawaban:
    - POST JSON valid -> simpan ke brief.yaml, cetak ANSWERS SAVED & NEXT: run gaps.py, exit 0.
    - Submit kedua -> 409 Conflict.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml"])
    proc, url, token, port = start_serve_process("kopi-senja", timeout=10)

    submit_url = f"http://127.0.0.1:{port}/{token}/submit"
    answers = {
        "audience": "mahasiswa dan penikmat kopi senja",
        "business.differentiator": "biji kopi lokal Jawa Barat",
    }
    payload = json.dumps(answers).encode("utf-8")

    req = urllib.request.Request(
        submit_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    resp = urllib.request.urlopen(req)
    assert resp.status == 200
    res_data = json.loads(resp.read().decode("utf-8"))
    # Submit kedua langsung harus menghasilkan 409 Conflict
    try:
        urllib.request.urlopen(req)
        assert False, "Submit kedua seharusnya menghasilkan 409 Conflict"
    except urllib.error.HTTPError as err:
        assert err.code == 409

    stdout, stderr = proc.communicate(timeout=5)
    assert proc.returncode == 0
    assert "ANSWERS SAVED" in stdout
    assert "NEXT: run gaps.py" in stdout

    # Periksa isi brief.yaml
    updated_brief = io.read_yaml(proj / "brief.yaml")
    assert updated_brief["audience"]["value"] == "mahasiswa dan penikmat kopi senja"
    assert updated_brief["audience"]["source"] == "stated"
    assert updated_brief["audience"]["note"] == "form"
    assert updated_brief["business"]["differentiator"]["value"] == "biji kopi lokal Jawa Barat"
    assert updated_brief["business"]["differentiator"]["source"] == "stated"
    assert updated_brief["business"]["differentiator"]["note"] == "form"
