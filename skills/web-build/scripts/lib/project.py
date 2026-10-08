# ============================================================
# File      : project.py
# Deskripsi : Pemuat bersama: folder proyek, brief, tipe situs, gaya,
#             pola layout, validasi skema, dan id requirement.
# ============================================================

from jsonschema import Draft202012Validator

from lib import io, paths
from lib.report import EXIT_INVALID, fail

# ============================================================
# ====================== FOLDER PROYEK =======================
# ============================================================


def open_project(slug, need=()):
    """
    Membuka folder proyek dan memastikan file yang dibutuhkan ada.

    I.S. : slug dari argumen baris perintah; need berisi nama file relatif.
    F.S. : Path folder proyek dikembalikan, atau ScriptExit kode 1 dengan petunjuk.
    """
    if not paths.is_valid_slug(slug):
        fail(EXIT_INVALID, f"Slug tidak sah: {slug!r} (pakai kebab-case huruf kecil).",
             "fix the slug and run the script again")

    project = paths.project_dir(slug)

    if not project.is_dir():
        fail(EXIT_INVALID, f"Folder proyek tidak ada: {project}",
             f"write projects/{slug}/brief.yaml first")

    missing = [name for name in need if not (project / name).is_file()]

    if missing:
        fail(EXIT_INVALID, [f"File belum ada: {project / name}" for name in missing],
             f"create {', '.join(missing)} first (see skills/web-build/SKILL.md)")

    return project


# ============================================================
# ========================= SKEMA ============================
# ============================================================


def schema_errors(data, schema_name):
    """
    Memvalidasi data terhadap satu skema di schemas/.

    I.S. : schema_name misalnya 'brief.schema.json'.
    F.S. : List baris '<path>: <pesan>' dikembalikan, terurut; kosong bila valid.
    """
    schema = io.read_json(paths.SCHEMAS_DIR / schema_name)
    validator = Draft202012Validator(schema)
    errors = []

    for error in validator.iter_errors(data):
        location = ".".join(str(part) for part in error.absolute_path) or "(root)"
        errors.append(f"{location}: {_schema_message(error)}")

    return sorted(set(errors))


def _schema_message(error):
    """
    Membuat pesan galat skema yang lebih jelas untuk aturan unknown.

    I.S. : error adalah ValidationError dari jsonschema.
    F.S. : Pesan galat dikembalikan.
    """
    if error.validator == "not" and list(error.absolute_path)[-1:] == ["value"]:
        return "value is 'unknown' but source is stated/inferred; set source: unknown or give a value"

    if error.validator == "const" and error.validator_value == "unknown":
        return "source is unknown, so value must be 'unknown'"

    return error.message


# ============================================================
# ========================== BRIEF ===========================
# ============================================================


def is_field(node):
    """
    Memeriksa apakah node adalah field brief ({value, source}).

    I.S. : node berupa nilai apa pun.
    F.S. : True bila node dict yang punya kunci value dan source.
    """
    return isinstance(node, dict) and "value" in node and "source" in node


def iter_fields(brief, prefix=""):
    """
    Menelusuri semua field brief sesuai urutan file.

    I.S. : brief adalah dict hasil parse brief.yaml.
    F.S. : Menghasilkan pasangan (path bertitik, field) untuk setiap field.
    """
    for key, node in brief.items():
        path = f"{prefix}{key}"

        if is_field(node):
            yield path, node
        elif isinstance(node, dict):
            yield from iter_fields(node, f"{path}.")


def get_field(brief, path):
    """
    Mengambil satu field brief dari path bertitik.

    I.S. : path misalnya 'business.location' atau 'audience'.
    F.S. : Field dikembalikan, atau None bila tidak ada.
    """
    node = brief

    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None

        node = node[part]

    return node if is_field(node) else None


def is_unknown(brief, path):
    """
    Memeriksa apakah field belum diketahui (tidak ada atau source unknown).

    I.S. : path seperti pada get_field.
    F.S. : True bila field tidak ada atau source-nya unknown.
    """
    field = get_field(brief, path)

    return field is None or field.get("source") == "unknown"


def requirements(brief):
    """
    Mengumpulkan requirement dari field stated dan inferred.

    I.S. : brief sudah lolos skema.
    F.S. : List {id, path, value, source} dikembalikan sesuai urutan file.
    """
    found = []

    for path, field in iter_fields(brief):
        if field["source"] in ("stated", "inferred"):
            found.append({
                "id": f"req-{path}",
                "path": path,
                "value": field["value"],
                "source": field["source"],
            })

    return found


def first_language(brief):
    """
    Mengambil bahasa pertama brief.

    I.S. : brief punya daftar languages.
    F.S. : Kode bahasa pertama dikembalikan ('id' bila kosong).
    """
    languages = brief.get("languages") or ["id"]

    return languages[0]


# ============================================================
# ==================== DATA SKILL (READ-ONLY) =================
# ============================================================


def load_site_type(site_type):
    """
    Memuat definisi tipe situs.

    I.S. : site_type adalah id yang sah.
    F.S. : dict tipe situs dikembalikan, atau ScriptExit kode 1 bila file tidak ada.
    """
    path = paths.site_type_file(site_type)

    if not path.is_file():
        fail(EXIT_INVALID, f"Tipe situs tidak dikenal: {site_type}",
             "set site_type to one of the files in skills/web-build/site-types/")

    return io.read_yaml(path)


def site_pages(brief, site_type):
    """
    Menentukan daftar halaman situs.

    I.S. : brief boleh berisi pages; site_type berisi default_pages.
    F.S. : List id halaman dikembalikan; halaman yang punya section selalu ikut.
    """
    pages = list(brief.get("pages") or site_type["default_pages"])

    for section in site_type["sections"]:
        if section["page"] not in pages:
            pages.append(section["page"])

    return pages


def load_style_index():
    """
    Memuat katalog gaya.

    I.S. : styles/index.yaml ada.
    F.S. : dict {id gaya: entri katalog} dikembalikan.
    """
    index = io.read_yaml(paths.STYLES_DIR / "index.yaml")

    return {entry["id"]: entry for entry in index["styles"]}


def load_style(style_id):
    """
    Memuat satu file gaya.

    I.S. : style_id terdaftar di styles/index.yaml.
    F.S. : dict gaya dikembalikan, atau None bila tidak terdaftar.
    """
    entry = load_style_index().get(style_id)

    return io.read_yaml(paths.STYLES_DIR / entry["file"]) if entry else None


def load_patterns():
    """
    Memuat pola layout per jenis section.

    I.S. : layouts/patterns.yaml ada.
    F.S. : dict {jenis: {id pola: entri}} dikembalikan.
    """
    raw = io.read_yaml(paths.PATTERNS_FILE)

    return {kind: {item["id"]: item for item in items} for kind, items in raw.items()}


def find_by_id(items, item_id):
    """
    Mencari satu entri berdasarkan id di list dict.

    I.S. : items berupa list dict yang punya kunci id.
    F.S. : Entri dikembalikan, atau None bila tidak ada.
    """
    return next((item for item in items if item.get("id") == item_id), None)

