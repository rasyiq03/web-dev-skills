# ============================================================
# File      : io.py
# Deskripsi : Baca dan tulis YAML/JSON dengan keluaran deterministik
#             (UTF-8, LF, urutan kunci tetap), hash SHA-256, dan
#             state.yaml milik setiap proyek.
# ============================================================

import hashlib
import json
import re
from pathlib import Path

import yaml

# ============================================================
# ========================== BACA ============================
# ============================================================


def read_text(path):
    """
    Membaca file teks UTF-8.

    I.S. : path menunjuk file yang ada.
    F.S. : Isi file dikembalikan dengan akhir baris dinormalkan ke LF.
    """
    return Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")


def read_yaml(path):
    """
    Membaca file YAML dengan loader aman.

    I.S. : path menunjuk file YAML yang ada.
    F.S. : Data hasil parse dikembalikan (dict, list, atau skalar).
    """
    return yaml.safe_load(read_text(path))


def read_json(path):
    """
    Membaca file JSON.

    I.S. : path menunjuk file JSON yang ada.
    F.S. : Data hasil parse dikembalikan.
    """
    return json.loads(read_text(path))


# ============================================================
# ========================== TULIS ===========================
# ============================================================


def write_text(path, text):
    """
    Menulis teks UTF-8 dengan akhir baris LF.

    I.S. : Folder induk boleh belum ada; text boleh mengandung CRLF.
    F.S. : File berisi text dengan akhir baris LF murni; folder induk dibuat bila perlu.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(normalized)



def to_json(data):
    """
    Mengubah data menjadi teks JSON yang stabil.

    I.S. : data dapat diserialisasi ke JSON.
    F.S. : Teks JSON berindentasi 2 spasi, karakter non-ASCII apa adanya, diakhiri LF.
    """
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_json(path, data):
    """
    Menulis data sebagai JSON yang stabil.

    I.S. : data dapat diserialisasi ke JSON.
    F.S. : File JSON tertulis lewat write_text.
    """
    write_text(path, to_json(data))


def to_yaml(data):
    """
    Mengubah data menjadi YAML blok dengan urutan kunci dipertahankan.

    I.S. : data berisi tipe dasar (dict, list, str, angka, bool, None).
    F.S. : Teks YAML dikembalikan; baris tidak dilipat agar diff tetap rapi.
    """
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=10_000,
    )


def write_yaml(path, data, header=None):
    """
    Menulis data sebagai YAML, dengan komentar pembuka bila diberikan.

    I.S. : data berisi tipe dasar.
    F.S. : File YAML tertulis; header (bila ada) menjadi baris komentar di awal file.
    """
    prefix = "".join(f"# {line}\n" for line in header.splitlines()) if header else ""
    write_text(path, prefix + to_yaml(data))


# ============================================================
# ====================== SKALAR YAML =========================
# ============================================================

INDICATOR_START = tuple("-?:,[]{}#&*!|>'\"%@`")
FLOW_FORBIDDEN = re.compile(r"[,\[\]{}]")


def yaml_scalar(value, flow=False):
    """
    Menulis satu skalar YAML: polos bila aman, kutip ganda bila tidak.

    I.S. : value berupa str, int, float, bool, atau None.
    F.S. : Teks skalar dikembalikan. String dikutip bila berisi ':' atau '=', diawali
           karakter indikator, berubah makna saat di-parse, atau (flow=True) berisi spasi
           atau karakter flow. Kutip ganda memakai escape JSON, yang sah di YAML.
    """
    if not isinstance(value, str):
        return yaml.safe_dump(value, default_flow_style=True).split("\n")[0]

    if _needs_quotes(value, flow):
        return json.dumps(value, ensure_ascii=False)

    return value


def _needs_quotes(text, flow):
    """
    Menentukan apakah string harus dikutip.

    I.S. : text berupa string.
    F.S. : True bila text tidak aman sebagai skalar polos.
    """
    if not text or text != text.strip():
        return True

    if ":" in text or "=" in text or " #" in text:
        return True

    if text.startswith(INDICATOR_START) and not re.match(r"^-[^\s-]|^--\S", text):
        return True

    if flow and (" " in text or FLOW_FORBIDDEN.search(text)):
        return True

    try:
        return yaml.safe_load(text) != text
    except yaml.YAMLError:
        return True


def yaml_flow_list(items):
    """
    Menulis list skalar dalam gaya flow, misalnya [a, b].

    I.S. : items berupa list skalar.
    F.S. : Teks list flow dikembalikan.
    """
    return "[" + ", ".join(yaml_scalar(item, flow=True) for item in items) + "]"


def yaml_flow_map(mapping):
    """
    Menulis dict skalar dalam gaya flow, misalnya { id: a, kind: b }.

    I.S. : mapping berupa dict dengan nilai skalar.
    F.S. : Teks mapping flow dikembalikan.
    """
    pairs = ", ".join(f"{key}: {yaml_scalar(val, flow=True)}" for key, val in mapping.items())

    return "{ " + pairs + " }"


# ============================================================
# =========================== HASH ===========================
# ============================================================


def sha256_bytes(data):
    """
    Menghitung SHA-256 dari bytes.

    I.S. : data berupa bytes.
    F.S. : Hash heksadesimal huruf kecil dikembalikan.
    """
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    """
    Menghitung SHA-256 isi file.

    I.S. : path menunjuk file yang ada.
    F.S. : Hash heksadesimal dikembalikan.
    """
    return sha256_bytes(Path(path).read_bytes())


# ============================================================
# ======================== STATE.YAML ========================
# ============================================================


def load_state(project):
    """
    Membaca state.yaml proyek.

    I.S. : project adalah folder proyek; state.yaml boleh belum ada.
    F.S. : dict state dikembalikan (kosong bila file belum ada).
    """
    path = Path(project) / "state.yaml"

    return (read_yaml(path) or {}) if path.is_file() else {}


def save_state(project, **updates):
    """
    Memperbarui state.yaml proyek.

    I.S. : project adalah folder proyek yang ada.
    F.S. : Kunci di updates ditimpa; kunci lain dipertahankan; state baru dikembalikan.
    """
    state = load_state(project)
    state.update(updates)
    write_yaml(Path(project) / "state.yaml", state, header="Ditulis oleh skrip web-build.")

    return state

