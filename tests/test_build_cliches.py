# ============================================================
# File      : test_build_cliches.py
# Deskripsi : Pengujian tools/build_cliches.py pada korpus buatan: frasa
#             yang dipakai banyak model untuk banyak brief terpilih; nama
#             usaha, frasa satu model, dan frasa kata fungsi tidak.
# ============================================================

import json

from conftest import REPO, run_script


def write_run(root, name, model, brief, body, lang="id"):
    folder = root / name
    (folder / "site").mkdir(parents=True)
    (folder / "meta.json").write_text(json.dumps({"model": model, "brief": brief, "condition": "C0"}), encoding="utf-8")
    (folder / "site" / "index.html").write_text(
        f'<!doctype html><html lang="{lang}"><body><main><p>{body}</p><p>[[ISI: harga]]</p></main></body></html>',
        encoding="utf-8")


def test_cliches_are_shared_across_models_and_briefs(tmp_path):
    runs = tmp_path / "runs"
    common = "Kami menghadirkan solusi terbaik untuk kebutuhan Anda."
    for model in ("model-a", "model-b"):
        write_run(runs, f"{model}-kopi", model, "kopi-senja", f"Kopi Senja di Bandung. {common} Untuk Anda dan kami.")
        write_run(runs, f"{model}-klinik", model, "klinik", f"Klinik Senyum Sehat di Surabaya. {common}")
    write_run(runs, "model-a-only", "model-a", "batik", "Batik tulis warisan leluhur. Batik tulis warisan leluhur.")
    out = tmp_path / "cliches-id.txt"

    result = run_script("build_cliches", str(runs), "--lang", "id", "--out", str(out), script_dir=REPO / "tools")

    assert result.returncode == 0, result.stdout + result.stderr
    phrases = [line for line in out.read_text(encoding="utf-8").splitlines() if not line.startswith("#")]
    # Frasa enam kata tertangkap sebagai 5-gram yang bertumpuk (batas atas n = 5)
    assert "kami menghadirkan solusi terbaik untuk" in phrases
    assert "solusi terbaik untuk kebutuhan anda" in phrases
    # Bagian frasa panjang tidak diulang sendiri-sendiri
    assert "solusi terbaik" not in phrases
    assert not any("senja" in p or "klinik" in p or "batik" in p for p in phrases)
    assert "untuk anda" not in phrases
    assert not any("isi" in p.split() for p in phrases)


def test_one_model_is_not_enough(tmp_path):
    runs = tmp_path / "runs"
    write_run(runs, "a1", "model-a", "kopi", "Solusi terbaik untuk Anda.")
    write_run(runs, "a2", "model-a", "klinik", "Solusi terbaik untuk Anda.")

    result = run_script("build_cliches", str(runs), "--out", str(tmp_path / "x.txt"), script_dir=REPO / "tools")

    assert result.returncode == 1
    assert "two or more models" in result.stdout
