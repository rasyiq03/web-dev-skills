# ============================================================
# File      : paths.py
# Deskripsi : Lokasi tetap di repo dan folder proyek, versi alat,
#             dan tanggal yang dipakai di header file.
# ============================================================

import datetime
import os
import re
from pathlib import Path

# ============================================================
# ========================= KONSTANTA ========================
# ============================================================

VERSION = "0.1"
TOOL_NAME = "pd-web-skills"
GENERATOR = f"{TOOL_NAME} {VERSION}"

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Folder di dalam site/ yang bukan bagian situs (misalnya repo git untuk deploy);
# tidak ikut disalin ke rounds/ dan tidak ikut di-hash di provenance.json
SITE_IGNORED_DIRS = (".git",)


# ============================================================
# ========================= AKAR REPO ========================
# ============================================================


def find_repo_root(start):
    """
    Mencari akar repo atau plugin dengan naik dari folder start.

    I.S. : start adalah folder di dalam repo, folder plugin terpasang, atau salinan skill
           (misalnya .agents/skills/web-build/scripts/lib untuk Codex).
    F.S. : Folder induk pertama yang berisi audit/anti-slop.yaml dan config/eslint.config.js
           dikembalikan; RuntimeError bila tidak ada.
    """
    start = Path(start).resolve()

    for folder in (start, *start.parents):
        if (folder / "audit" / "anti-slop.yaml").is_file() and (folder / "config" / "eslint.config.js").is_file():
            return folder

    raise RuntimeError(f"Akar web-skills (audit/ dan config/) tidak ditemukan di atas {start}")


REPO_ROOT = find_repo_root(Path(__file__).parent)
SKILLS_DIR = REPO_ROOT / "skills"
BUILD_DIR = SKILLS_DIR / "web-build"
SCRIPTS_DIR = BUILD_DIR / "scripts"
DESIGN_DIR = SKILLS_DIR / "web-design"
SCHEMAS_DIR = BUILD_DIR / "schemas"
SITE_TYPES_DIR = BUILD_DIR / "site-types"
TEMPLATES_DIR = BUILD_DIR / "templates"
REFERENCES_DIR = BUILD_DIR / "references"
STYLES_DIR = DESIGN_DIR / "styles"
PATTERNS_FILE = DESIGN_DIR / "layouts" / "patterns.yaml"
AUDIT_DIR = REPO_ROOT / "audit"
CONFIG_DIR = REPO_ROOT / "config"


def repo_root():
    """
    Mengembalikan root repository.

    I.S. : -
    F.S. : Path REPO_ROOT dikembalikan.
    """
    return REPO_ROOT


def scripts_dir():
    """
    Mengembalikan folder skills/web-build/scripts.

    I.S. : -
    F.S. : Path SCRIPTS_DIR dikembalikan.
    """
    return SCRIPTS_DIR


def node_modules_dir():
    """
    Menentukan folder node_modules yang dipakai alat Node.

    I.S. : PD_NODE_MODULES boleh diatur (run.py mengisinya dengan folder cache).
    F.S. : Path PD_NODE_MODULES dikembalikan bila diatur, selain itu node_modules di akar repo.
           Dibaca setiap dipanggil karena run.py mengaturnya setelah modul ini diimpor.
    """
    override = os.environ.get("PD_NODE_MODULES")

    return Path(override) if override else REPO_ROOT / "node_modules"


# ============================================================
# ====================== FOLDER PROYEK =======================
# ============================================================


def projects_dir():
    """
    Menentukan folder induk semua proyek.

    I.S. : PD_PROJECTS_DIR boleh diatur; folder kerja saat ini menentukan sisanya.
    F.S. : Urutan: PD_PROJECTS_DIR; projects/ di akar repo bila folder kerja adalah akar repo
           (mode pengembangan); selain itu folder kerja itu sendiri, sehingga proyek ada di
           <folder>/<slug>/. Path belum tentu sudah ada.
    """
    override = os.environ.get("PD_PROJECTS_DIR")

    if override:
        return Path(override)

    cwd = Path.cwd().resolve()

    if cwd == REPO_ROOT:
        return REPO_ROOT / "projects"

    return cwd


def find_project_home(slug):
    """
    Mencari folder induk proyek dari folder kerja, untuk agen yang pindah ke dalam proyek.

    I.S. : slug sudah sah; folder kerja boleh berada di dalam folder proyek (misalnya site/).
    F.S. : Folder yang memuat <slug>/brief.yaml, bila <slug> adalah folder kerja atau salah
           satu induknya, dikembalikan; None bila tidak ada.
    """
    cwd = Path.cwd().resolve()

    for folder in (cwd, *cwd.parents):
        if folder.name == slug and (folder / "brief.yaml").is_file():
            return folder.parent

    return None


def is_valid_slug(slug):
    """
    Memeriksa apakah slug berbentuk kebab-case huruf kecil.

    I.S. : slug berupa string apa pun.
    F.S. : True bila slug sah, False bila tidak.
    """
    return bool(SLUG_PATTERN.match(slug or ""))


def project_dir(slug):
    """
    Mengembalikan folder satu proyek.

    I.S. : slug sudah diperiksa dengan is_valid_slug.
    F.S. : Path <folder induk proyek>/<slug>/ dikembalikan (lihat projects_dir).
    """
    return projects_dir() / slug


def site_type_file(site_type):
    """
    Mengembalikan file definisi satu tipe situs.

    I.S. : site_type adalah id tipe situs, misalnya company-profile.
    F.S. : Path site-types/<site_type>.yaml dikembalikan.
    """
    return SITE_TYPES_DIR / f"{site_type}.yaml"


def page_file(page):
    """
    Mengembalikan path relatif file HTML untuk satu halaman.

    I.S. : page adalah id halaman dari tipe situs, misalnya index atau tentang.
    F.S. : 'index.html' untuk index, 'pages/<page>.html' untuk lainnya.
    """
    return "index.html" if page == "index" else f"pages/{page}.html"


# ============================================================
# ========================== TANGGAL =========================
# ============================================================


def today(state=None):
    """
    Menentukan tanggal untuk header file dan template.

    I.S. : state boleh berisi 'created'; PD_DATE boleh diatur.
    F.S. : Tanggal ISO dikembalikan. Urutan: PD_DATE, state['created'], hari ini.
           Tanggal proyek tetap sama di setiap run sehingga keluaran byte-identik.
    """
    override = os.environ.get("PD_DATE")

    if override:
        return override

    if state and state.get("created"):
        return str(state["created"])

    return datetime.date.today().isoformat()

