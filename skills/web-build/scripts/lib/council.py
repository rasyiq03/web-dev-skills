# ============================================================
# File      : council.py
# Proyek    : ScaffolDev
# Deskripsi : Dewan AI untuk mode deep work: peran, sidang, aturan
#             musyawarah untuk mufakat, dan pemeriksaan notulen. Agen
#             menjalankan sidangnya; modul ini menjaga aturannya.
# ============================================================

from lib import graph, io, project

# ============================================================
# ========================= KONSTANTA ========================
# ============================================================

# Anggota yang bersuara; pimpinan sidang (agen utama) memimpin dan mencatat
MEMBERS = ("perancang", "penulis", "arsitek", "penguji", "wakil-klien")
CHAIR = "pimpinan"

ROLE_NAMES = {
    "pimpinan": "Pimpinan sidang",
    "perancang": "Perancang",
    "penulis": "Penulis",
    "arsitek": "Arsitek front-end",
    "penguji": "Penguji mutu",
    "wakil-klien": "Wakil klien",
}

SITTINGS = ("direction", "copy", "first-page", "site")

SITTING_NAMES = {
    "direction": "Sidang arah desain",
    "copy": "Sidang isi teks",
    "first-page": "Sidang halaman pertama",
    "site": "Sidang seluruh situs",
}

# Peran yang suaranya dihitung dua kali per sidang, karena topik itu keahliannya
TOPIC_OWNER = {"direction": "perancang", "copy": "penulis", "first-page": "penguji", "site": "penguji"}

# Langkah web-build saat sidang itu diadakan
SITTING_STEP = {"direction": 3, "copy": 5, "first-page": 6, "site": 7}

MAX_ROUNDS = 3
MINUTES_DIR = "deliberation"


# ============================================================
# ========================== SUARA ===========================
# ============================================================


def weighted_outcome(sitting, votes):
    """
    Menghitung hasil voting berbobot: pemilik topik dua suara, anggota lain satu.

    I.S. : votes adalah daftar {role, choice}.
    F.S. : Pilihan dengan bobot terbesar dikembalikan; bila seri, pilihan pemilik topik
           menang; None bila tidak ada suara.
    """
    owner = TOPIC_OWNER[sitting]
    totals = {}

    for vote in votes:
        totals[vote["choice"]] = totals.get(vote["choice"], 0) + (2 if vote["role"] == owner else 1)

    if not totals:
        return None

    best = max(totals.values())
    leaders = [choice for choice, total in totals.items() if total == best]
    owner_choice = next((v["choice"] for v in votes if v["role"] == owner), None)

    return owner_choice if len(leaders) > 1 and owner_choice in leaders else leaders[0]


# ============================================================
# ========================= NOTULEN ==========================
# ============================================================


def _round_errors(minutes, context_graph):
    """
    Memeriksa putaran: semua anggota didengar, gotong royong di kritik, dan bukti yang sah.

    I.S. : minutes sudah lolos skema.
    F.S. : Daftar pesan galat dikembalikan.
    """
    errors = []
    rounds = minutes["rounds"]

    if [r["round"] for r in rounds] != list(range(1, len(rounds) + 1)):
        errors.append("Nomor putaran harus berurutan mulai dari 1.")

    if rounds[0]["kind"] != "proposals":
        errors.append("Putaran 1 harus usulan mandiri (kind: proposals).")

    if len(rounds) < 2 or rounds[1]["kind"] != "critique":
        errors.append("Putaran 2 harus saling menanggapi (kind: critique).")

    for number, kind in ((0, "proposals"), (1, "critique")):
        if number < len(rounds) and rounds[number]["kind"] == kind:
            spoke = [e["role"] for e in rounds[number]["entries"]]

            if sorted(spoke) != sorted(MEMBERS):
                errors.append(f"Putaran {number + 1}: setiap anggota bicara tepat sekali (yang bicara: {', '.join(spoke)}).")

    if len(rounds) > 1:
        for entry in rounds[1]["entries"]:
            if not entry.get("target_role") or entry["target_role"] == entry["role"]:
                errors.append(f"Putaran 2: {entry['role']} harus memperbaiki usulan anggota lain dulu (isi target_role).")

    for r in rounds:
        for entry in r["entries"]:
            if entry.get("blocking") and not entry.get("evidence"):
                errors.append(f"Putaran {r['round']}: keberatan {entry['role']} memblokir tanpa bukti; sebut id simpul graf.")

            for ref in entry.get("evidence", []):
                if graph.resolve(context_graph, ref) is None:
                    errors.append(f"Putaran {r['round']}: bukti {ref!r} dari {entry['role']} tidak ada di graf.")

    return errors


def _resolution_errors(minutes, directions_data):
    """
    Memeriksa keputusan sidang: aturan mufakat, voting berbobot, dan hasil arah yang sah.

    I.S. : minutes sudah lolos skema.
    F.S. : Daftar pesan galat dikembalikan.
    """
    errors = []
    resolution = minutes["resolution"]
    sitting = minutes["sitting"]
    open_blocks = [
        e["role"] for r in minutes["rounds"] for e in r["entries"] if e.get("blocking") and not e.get("resolved")
    ]

    if resolution["method"] == "mufakat" and open_blocks:
        errors.append(f"Mufakat belum tercapai: keberatan dari {', '.join(open_blocks)} masih memblokir. Revisi lagi atau lakukan voting.")

    if resolution["method"] == "vote":
        voters = sorted(v["role"] for v in resolution.get("votes", []))

        if voters != sorted(MEMBERS):
            errors.append("Voting harus memuat tepat satu suara dari setiap anggota.")
        else:
            winner = weighted_outcome(sitting, resolution["votes"])

            if winner != resolution["outcome"]:
                errors.append(f"Hasil voting berbobot adalah {winner!r}, bukan {resolution['outcome']!r}.")

    if sitting == "direction":
        ids = [d.get("id") for d in directions_data.get("directions", [])]

        if resolution["outcome"] not in ids:
            errors.append(f"Hasil sidang arah harus salah satu dari {', '.join(ids)}.")

    return errors


def validate_minutes(minutes, context_graph, directions_data):
    """
    Memeriksa notulen satu sidang terhadap skema dan aturan musyawarah.

    I.S. : minutes dibaca dari deliberation/<sidang>.yaml.
    F.S. : Daftar pesan galat dikembalikan; kosong bila notulen sah.
    """
    errors = project.schema_errors(minutes, "deliberation.schema.json")

    if errors:
        return [f"Skema notulen: {err}" for err in errors]

    if sorted(minutes["roles"]) != sorted(MEMBERS):
        errors.append(f"Semua anggota harus hadir: {', '.join(MEMBERS)}.")

    return errors + _round_errors(minutes, context_graph) + _resolution_errors(minutes, directions_data)


def read_all(proj_dir):
    """
    Membaca semua notulen yang sudah tercatat di folder deliberation/.

    I.S. : Folder boleh belum ada.
    F.S. : dict {sidang: notulen} dikembalikan, urut menurut SITTINGS.
    """
    folder = proj_dir / MINUTES_DIR
    found = {}

    for sitting in SITTINGS:
        path = folder / f"{sitting}.yaml"

        if path.is_file():
            found[sitting] = io.read_yaml(path) or {}

    return found
