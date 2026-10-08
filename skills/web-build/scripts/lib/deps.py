# ============================================================
# File      : deps.py
# Deskripsi : Memastikan paket Python dan alat Node tersedia sebelum skrip
#             berjalan: pakai yang sudah ada, atau pasang sekali ke folder
#             cache pengguna. Hanya memakai pustaka standar dan lib.report,
#             karena modul ini berjalan sebelum paket pihak ketiga terpasang.
# ============================================================

import functools
import hashlib
import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from lib.report import EXIT_INVALID, fail

# ============================================================
# ========================= KONSTANTA ========================
# ============================================================

# Nama modul yang diimpor skrip (bukan nama paket pip)
PYTHON_MODULES = ("yaml", "jsonschema", "bs4", "tinycss2")

NODE_MANIFESTS = ("package.json", "package-lock.json")


# ============================================================
# =========================== CACHE ==========================
# ============================================================


def cache_root():
    """
    Menentukan folder cache dependensi milik pengguna.

    I.S. : PD_CACHE_DIR, LOCALAPPDATA, atau XDG_CACHE_HOME boleh diatur.
    F.S. : Urutan: PD_CACHE_DIR; %LOCALAPPDATA%/web-skills di Windows;
           $XDG_CACHE_HOME/web-skills; ~/.cache/web-skills. Path belum tentu ada.
    """
    override = os.environ.get("PD_CACHE_DIR")

    if override:
        return Path(override)

    local_app_data = os.environ.get("LOCALAPPDATA")

    if os.name == "nt" and local_app_data:
        return Path(local_app_data) / "web-skills"

    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"

    return base / "web-skills"


def file_hash(path):
    """
    Menghitung sidik pendek isi file untuk nama folder cache.

    I.S. : path adalah file yang ada.
    F.S. : 12 karakter heksadesimal pertama SHA-256 isi file dikembalikan.
    """
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def output_tail(result):
    """
    Meringkas keluaran installer yang gagal.

    I.S. : result adalah CompletedProcess installer.
    F.S. : Paling banyak 8 baris terakhir stderr (atau stdout), masing-masing diindentasi.
    """
    text = (result.stderr or result.stdout or "").strip()

    return ["  " + line for line in text.splitlines()[-8:]]


def install_into(final, label, install):
    """
    Memasang dependensi ke folder sementara lalu me-rename-nya menjadi folder akhir.

    I.S. : final belum ada; install(tmp) menjalankan installer ke folder tmp dan
           mengembalikan CompletedProcess.
    F.S. : final berisi hasil instalasi lengkap. Bila installer gagal, folder sementara
           dihapus dan ScriptExit kode 1 dilempar, jadi folder akhir yang ada selalu lengkap.
    """
    tmp = final.with_name(f"{final.name}.tmp-{os.getpid()}")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    print(f"Menyiapkan {label} sekali saja di {final} ...", flush=True)

    result = install(tmp)

    if result.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        fail(
            EXIT_INVALID,
            [f"Pemasangan {label} gagal (kode keluar {result.returncode}):"] + output_tail(result),
            f"tell the user that installing {label} failed (see the lines above; usually no "
            "internet connection), then run the same command again",
        )

    try:
        tmp.rename(final)
    except OSError:
        # Proses lain selesai lebih dulu; hasilnya dipakai
        shutil.rmtree(tmp, ignore_errors=True)

        if not final.is_dir():
            raise


# ============================================================
# ======================= PAKET PYTHON =======================
# ============================================================


def python_packages_importable():
    """
    Memeriksa apakah interpreter ini sudah bisa mengimpor semua paket.

    I.S. : -
    F.S. : True bila setiap modul di PYTHON_MODULES ditemukan.
    """
    return all(importlib.util.find_spec(name) is not None for name in PYTHON_MODULES)


def pip_install(requirements, tmp):
    """
    Memasang requirements.txt ke folder tmp dengan pip --target.

    I.S. : requirements adalah path requirements.txt; tmp folder kosong.
    F.S. : CompletedProcess pip dikembalikan.
    """
    command = [
        sys.executable, "-m", "pip", "install",
        "--disable-pip-version-check", "--no-input", "--quiet",
        "--target", str(tmp), "-r", str(requirements),
    ]

    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8")


def ensure_python_packages(repo_root, cache):
    """
    Memastikan paket Python di requirements.txt bisa diimpor.

    I.S. : repo_root berisi requirements.txt; cache adalah folder cache pengguna.
    F.S. : None bila interpreter sudah punya paketnya. Selain itu folder
           <cache>/py-<versi>-<hash> (dipasang dulu bila belum ada) ditambahkan ke awal
           sys.path dan dikembalikan. ScriptExit kode 1 bila pip gagal.
    """
    if python_packages_importable():
        return None

    requirements = Path(repo_root) / "requirements.txt"
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    target = Path(cache) / f"py-{version}-{file_hash(requirements)}"

    if not target.is_dir():
        install_into(target, "paket Python (pip)", functools.partial(pip_install, requirements))

    sys.path.insert(0, str(target))
    importlib.invalidate_caches()

    return target


# ============================================================
# ========================= ALAT NODE ========================
# ============================================================


def node_packages(repo_root):
    """
    Membaca nama paket Node yang dibutuhkan dari package.json.

    I.S. : repo_root berisi package.json.
    F.S. : List nama paket di dependencies dan devDependencies, terurut.
    """
    manifest = json.loads((Path(repo_root) / "package.json").read_text(encoding="utf-8"))
    names = {**manifest.get("dependencies", {}), **manifest.get("devDependencies", {})}

    return sorted(names)


def node_modules_complete(folder, packages):
    """
    Memeriksa apakah sebuah node_modules memuat semua paket.

    I.S. : folder boleh belum ada.
    F.S. : True bila setiap paket punya package.json di folder itu.
    """
    return all((folder / name / "package.json").is_file() for name in packages)


def npm_ci(repo_root, npm, tmp):
    """
    Memasang alat Node persis sesuai package-lock.json ke folder tmp.

    I.S. : npm adalah path perintah npm; tmp folder kosong.
    F.S. : package.json dan package-lock.json tersalin ke tmp; CompletedProcess npm ci
           dikembalikan.
    """
    for name in NODE_MANIFESTS:
        shutil.copyfile(Path(repo_root) / name, tmp / name)

    command = [npm, "ci", "--no-audit", "--no-fund", "--loglevel=error"]

    return subprocess.run(command, cwd=tmp, capture_output=True, text=True, encoding="utf-8")


def ensure_node_tools(repo_root, cache):
    """
    Memastikan alat Node di package.json tersedia.

    I.S. : repo_root berisi package.json dan package-lock.json; cache adalah folder cache.
    F.S. : node_modules repo dikembalikan bila lengkap. Selain itu
           <cache>/node-<hash>/node_modules (dipasang dulu dengan npm ci bila belum ada)
           dikembalikan. ScriptExit kode 1 bila node/npm tidak ada atau npm ci gagal.
    """
    repo_root = Path(repo_root)
    packages = node_packages(repo_root)
    local = repo_root / "node_modules"

    if node_modules_complete(local, packages):
        return local

    final = Path(cache) / f"node-{file_hash(repo_root / 'package-lock.json')}"

    if not final.is_dir():
        npm = shutil.which("npm")

        if npm is None or shutil.which("node") is None:
            fail(
                EXIT_INVALID,
                [
                    "Node.js (perintah node dan npm) tidak ditemukan di PATH.",
                    "Pasang Node.js versi LTS dari https://nodejs.org, lalu buka terminal baru.",
                ],
                "tell the user to install Node.js LTS from https://nodejs.org and open a new "
                "terminal, then run the same command again",
            )

        install_into(final, "alat Node (npm ci)", functools.partial(npm_ci, repo_root, npm))

    return final / "node_modules"
