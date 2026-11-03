# ============================================================
# File      : build_cliches.py
# Proyek    : ScaffolDev
# Deskripsi : Menyusun daftar klise dari situs yang dibangun banyak model
#             (keluaran tools/eval/harness.py): n-gram 2-5 kata yang muncul
#             di sedikitnya 20% keluaran dari sedikitnya dua model, untuk
#             sedikitnya dua brief berbeda. Hasilnya menggantikan daftar
#             benih audit/cliches-<lang>.txt.
# ============================================================

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "skills" / "web-build" / "scripts"))

from bs4 import BeautifulSoup  # noqa: E402
from lib import io, report  # noqa: E402
from lib.report import EXIT_INVALID, fail  # noqa: E402

MIN_SHARE = 0.20  # bagian keluaran satu model yang memuat frasa
MIN_MODELS = 2
MIN_BRIEFS = 2  # frasa yang hanya muncul untuk satu brief adalah isi brief, bukan klise
NGRAMS = range(2, 6)

# Kata fungsi: frasa yang hanya berisi kata ini terlalu umum untuk disebut klise
STOPWORDS = {
    "id": set("dan yang di ke dari untuk dengan ini itu atau pada dalam juga kami kita anda kamu "
              "adalah akan bisa ada tidak lebih sangat para setiap semua oleh karena agar serta "
              "sebagai saat kini telah sudah hanya lagi pun nya".split()),
    "en": set("the a an and or of to in on for with by from at as is are be this that it its your "
              "you we our us all every more very can will not into over than just".split()),
}

WORD = re.compile(r"[a-zA-ZÀ-ÿ]+(?:-[a-zA-ZÀ-ÿ]+)*")


# ============================================================
# ========================== KORPUS ==========================
# ============================================================


def visible_text(site_dir, lang):
    """
    Mengambil teks yang tampak dari halaman situs berbahasa lang.

    I.S. : site_dir berisi halaman HTML (folder .ScaffolDev dan node_modules dilewati).
    F.S. : Satu string berisi teks semua halaman dengan <html lang> yang cocok.
    """
    parts = []
    for page in sorted(Path(site_dir).rglob("*.html")):
        if ".ScaffolDev" in page.parts or "node_modules" in page.parts:
            continue
        soup = BeautifulSoup(page.read_text(encoding="utf-8", errors="replace"), "html.parser")
        if (soup.html.get("lang", "") if soup.html else "").split("-")[0] != lang:
            continue
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        # Placeholder [[ISI: ...]] bukan tulisan model
        parts.append(re.sub(r"\[\[ISI:[^\]]*\]\]", " ", soup.get_text(" ")))
    return " ".join(parts)


def ngrams(text):
    """
    Mengumpulkan n-gram 2-5 kata dari satu teks, tanpa memotong kalimat.

    I.S. : text adalah teks tampak satu keluaran.
    F.S. : Himpunan frasa huruf kecil dikembalikan (kehadiran, bukan jumlah).
    """
    found = set()
    for sentence in re.split(r"[.!?:;•|\n]+", text):
        words = [w.lower() for w in WORD.findall(sentence)]
        for n in NGRAMS:
            for i in range(len(words) - n + 1):
                found.add(" ".join(words[i:i + n]))
    return found


def load_runs(run_dirs, lang):
    """
    Membaca setiap keluaran harness: meta.json dan situs di sebelahnya.

    I.S. : run_dirs berisi folder yang di dalamnya ada <run>/meta.json.
    F.S. : Daftar (model, brief, frasa) dikembalikan; run tanpa teks berbahasa lang dilewati.
    """
    runs = []
    for root in run_dirs:
        for meta_file in sorted(Path(root).rglob("meta.json")):
            meta = io.read_json(meta_file)
            site = meta_file.parent / meta.get("site", "site")
            text = visible_text(site, lang)
            if text.strip():
                runs.append((meta["model"], meta["brief"], ngrams(text)))
    return runs


# ============================================================
# ========================== SELEKSI =========================
# ============================================================


def select_cliches(runs, lang):
    """
    Memilih frasa yang dipakai berulang oleh beberapa model untuk beberapa brief.

    I.S. : runs dari load_runs().
    F.S. : Daftar (frasa, model, brief) urut: paling banyak model, lalu brief, lalu abjad.
           Frasa yang semuanya kata fungsi dibuang, juga frasa pendek yang hampir selalu
           muncul sebagai bagian frasa panjang yang terpilih.
    """
    per_model = defaultdict(int)
    hits = defaultdict(lambda: defaultdict(int))
    briefs = defaultdict(set)

    for model, brief, phrases in runs:
        per_model[model] += 1
        for phrase in phrases:
            hits[phrase][model] += 1
            briefs[phrase].add(brief)

    stop = STOPWORDS.get(lang, set())
    chosen = {}
    for phrase, by_model in hits.items():
        models = [m for m, count in by_model.items() if count / per_model[m] >= MIN_SHARE]
        if len(models) >= MIN_MODELS and len(briefs[phrase]) >= MIN_BRIEFS:
            if not all(word in stop for word in phrase.split()):
                chosen[phrase] = (len(models), len(briefs[phrase]), sum(by_model.values()))

    def covered(phrase):
        total = chosen[phrase][2]
        return any(phrase in longer and longer != phrase and chosen[longer][2] >= 0.8 * total
                   for longer in chosen)

    kept = [p for p in chosen if not covered(p)]
    return sorted(((p, chosen[p][0], chosen[p][1]) for p in kept), key=lambda x: (-x[1], -x[2], x[0]))


def write_list(out, lang, cliches, runs):
    """
    Menulis daftar klise dengan kepala yang menjelaskan asal dan aturannya.

    I.S. : cliches dari select_cliches(); runs dari load_runs().
    F.S. : File out berisi satu frasa per baris (huruf kecil), siap dibaca check.py.
    """
    models = sorted({model for model, _, _ in runs})
    lines = [
        f"# Dibuat oleh tools/build_cliches.py dari {len(runs)} situs berbahasa {lang} "
        f"({len(models)} model: {', '.join(models)}).",
        f"# Aturan: n-gram 2-5 kata di >= {int(MIN_SHARE * 100)}% keluaran dari >= {MIN_MODELS} model, "
        f"untuk >= {MIN_BRIEFS} brief; frasa kata fungsi dibuang.",
        "# One phrase per line, lowercase; check.py matches them case-insensitively in visible text.",
    ] + [phrase for phrase, _, _ in cliches]
    io.write_text(out, "\n".join(lines) + "\n")


def main():
    """
    Titik masuk CLI.

    I.S. : sys.argv berisi folder hasil harness dan opsi --lang/--out.
    F.S. : Daftar klise ditulis; ringkasan dan NEXT dikembalikan.
    """
    parser = argparse.ArgumentParser(description="Menyusun daftar klise dari keluaran harness evaluasi.")
    parser.add_argument("runs", nargs="+", help="folder hasil tools/eval/harness.py")
    parser.add_argument("--lang", default="id", choices=sorted(STOPWORDS))
    parser.add_argument("--out", help="bawaan: audit/cliches-<lang>.txt")
    args = parser.parse_args()

    runs = load_runs(args.runs, args.lang)
    if len({model for model, _, _ in runs}) < MIN_MODELS:
        fail(EXIT_INVALID, f"Butuh keluaran dari sedikitnya {MIN_MODELS} model; ditemukan {len(runs)} situs.",
             "run tools/eval/harness.py with two or more models first")

    out = Path(args.out) if args.out else REPO_ROOT / "audit" / f"cliches-{args.lang}.txt"
    cliches = select_cliches(runs, args.lang)
    write_list(out, args.lang, cliches, runs)

    lines = [f"{len(cliches)} klise dari {len(runs)} situs ditulis ke {out}:"]
    lines += [f"  - {phrase} ({models} model, {nbriefs} brief)" for phrase, models, nbriefs in cliches[:20]]
    return lines, "review the list, then commit it"


if __name__ == "__main__":
    report.run(main)
