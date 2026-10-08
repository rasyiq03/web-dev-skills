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

# scripts/lib/paths.py -> scripts -> web-build -> skills -> root repo
REPO_ROOT = Path(__file__).resolve().parents[4]
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
NODE_MODULES = REPO_ROOT / "node_modules"

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


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


# ============================================================
# ====================== FOLDER PROYEK =======================
# ============================================================


def projects_dir():
    """
    Menentukan folder induk semua proyek.

    I.S. : PD_PROJECTS_DIR boleh diatur (dipakai tes); bila tidak, pakai projects/ di root.
    F.S. : Path folder induk proyek dikembalikan (belum tentu sudah ada).
    """
    override = os.environ.get("PD_PROJECTS_DIR")

    return Path(override) if override else REPO_ROOT / "projects"


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
    F.S. : Path projects/<slug>/ dikembalikan.
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

