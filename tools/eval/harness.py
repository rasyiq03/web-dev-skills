# ============================================================
# File      : harness.py
# Proyek    : ScaffolDev
# Deskripsi : Harness evaluasi tanpa pengawasan (IMPLEMENTATION.md §3.11):
#             menjalankan brief yang sama di kondisi C0 (prompt saja), C1
#             (prompt + skill frontend-design Anthropic), dan C2 (ScaffolDev)
#             untuk beberapa model dan pengulangan, lalu mengukur setiap
#             situs di browser dan menulis satu CSV.
# ============================================================

import argparse
import csv
import itertools
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "web-build" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "tools"))
sys.path.insert(0, str(REPO_ROOT / "tools" / "render"))

import metrics  # noqa: E402
import render_check  # noqa: E402
import yaml  # noqa: E402
from build_cliches import visible_text  # noqa: E402
from lib import io, report  # noqa: E402
from lib.report import EXIT_INVALID, fail  # noqa: E402

CONDITIONS = ("C0", "C1", "C2")

# Perintah agen; {prompt}, {model}, dan {plugins} diisi per run. Hanya Claude Code yang sudah
# diuji; agen lain bisa diberikan lewat --agent-command dengan tempat isian yang sama.
CLAUDE = ("claude -p {prompt} --model {model} --output-format json --dangerously-skip-permissions "
          "--setting-sources project --max-budget-usd {budget} {plugins}")

COLUMNS = ["run", "condition", "model", "brief", "lang", "rep", "exit", "seconds", "input_tokens",
           "output_tokens", "cost_usd", "pages", "axe_errors", "axe_warnings", "overflow",
           "console_errors", "cliche_hits", "placeholders", "check_errors", "check_warnings", "dhi"]


# ============================================================
# ========================= MENJALANKAN ======================
# ============================================================


def plan(briefs, conditions, models, reps):
    """
    Menyusun daftar run: setiap kombinasi kondisi, model, brief, dan pengulangan.

    I.S. : Semua argumen berupa daftar tak kosong; reps bilangan bulat >= 1.
    F.S. : Daftar dict run dengan id stabil dikembalikan, urut deterministik.
    """
    runs = []
    for condition, model, brief, rep in itertools.product(conditions, models, briefs, range(1, reps + 1)):
        runs.append({"run": f"{condition}-{model}-{brief['id']}-{rep}".replace("/", "_"),
                     "condition": condition, "model": model, "brief": brief["id"],
                     "lang": brief["lang"], "prompt": brief["prompt"], "rep": rep})
    return runs


def plugin_args(condition, c1_plugin):
    """
    Menentukan plugin yang dimuat untuk satu kondisi.

    I.S. : c1_plugin adalah folder plugin frontend-design atau None.
    F.S. : Potongan argumen --plugin-dir dikembalikan (kosong untuk C0).
    """
    if condition == "C2":
        return f"--plugin-dir {shlex.quote(str(REPO_ROOT))}"
    if condition == "C1":
        return f"--plugin-dir {shlex.quote(str(c1_plugin))}"
    return ""


def run_agent(run, folder, command, c1_plugin, budget, timeout):
    """
    Menjalankan agen di folder kosong untuk satu run.

    I.S. : folder belum ada; command adalah templat perintah agen.
    F.S. : folder berisi keluaran agen dan agent.json; (kode keluar, detik, usage) dikembalikan.
    """
    folder.mkdir(parents=True)
    text = command.format(prompt=shlex.quote(run["prompt"]), model=shlex.quote(run["model"]),
                          plugins=plugin_args(run["condition"], c1_plugin), budget=budget)
    started = time.monotonic()
    try:
        result = subprocess.run(shlex.split(text), cwd=folder, capture_output=True, text=True,
                                encoding="utf-8", timeout=timeout)
        code, out = result.returncode, result.stdout
    except subprocess.TimeoutExpired as expired:
        code, out = -1, expired.stdout or ""
    seconds = round(time.monotonic() - started)
    (folder / "agent.json").write_text(out if isinstance(out, str) else out.decode(), encoding="utf-8")
    return code, seconds, usage(out)


def usage(output):
    """
    Membaca pemakaian token dan biaya dari keluaran JSON agen.

    I.S. : output adalah stdout agen (JSON dari --output-format json, atau teks lain).
    F.S. : dict input_tokens, output_tokens, cost_usd (kosong bila tidak terbaca).
    """
    try:
        data = json.loads(output if isinstance(output, str) else output.decode())
    except (ValueError, AttributeError):
        return {"input_tokens": "", "output_tokens": "", "cost_usd": ""}
    tokens = data.get("usage", {})
    total_in = sum(tokens.get(k, 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    return {"input_tokens": total_in, "output_tokens": tokens.get("output_tokens", ""),
            "cost_usd": data.get("total_cost_usd", "")}


# ============================================================
# ========================== MENGUKUR ========================
# ============================================================


def find_site(folder):
    """
    Mencari situs yang dibuat agen di folder run.

    I.S. : folder adalah folder kerja satu run.
    F.S. : Folder terdangkal yang berisi index.html dikembalikan (None bila tidak ada);
           node_modules, .ScaffolDev, dan folder tersembunyi dilewati.
    """
    candidates = [p.parent for p in folder.rglob("index.html")
                  if not any(part.startswith(".") or part == "node_modules" for part in p.relative_to(folder).parts)]
    return min(candidates, key=lambda p: (len(p.parts), str(p))) if candidates else None


def load_cliches(lang):
    """
    Membaca daftar klise audit/cliches-<lang>.txt.

    I.S. : File boleh belum ada.
    F.S. : Daftar frasa huruf kecil dikembalikan.
    """
    path = REPO_ROOT / "audit" / f"cliches-{lang}.txt"
    if not path.is_file():
        return []
    return [line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]


def measure(run, folder, site, browser):
    """
    Mengukur satu situs: hasil browser, klise, placeholder, dan hasil check ScaffolDev (C2).

    I.S. : site adalah folder situs atau None.
    F.S. : (kolom ukuran, sidik situs atau None) dikembalikan; meta.json ditulis untuk
           build_cliches.
    """
    row = {"pages": 0, "axe_errors": "", "axe_warnings": "", "overflow": "", "console_errors": "",
           "cliche_hits": "", "placeholders": "", "check_errors": "", "check_warnings": ""}
    if site is None:
        return row, None

    io.write_json(folder / "meta.json", {"model": run["model"], "brief": run["brief"],
                                          "condition": run["condition"], "site": os.path.relpath(site, folder)})
    pages = sorted(p.relative_to(site).as_posix() for p in site.rglob("*.html")
                   if not any(part.startswith(".") or part == "node_modules" for part in p.relative_to(site).parts))
    results = render_check.run_browser(site, folder, browser, pages)
    findings = render_check.page_findings(results)
    html = " ".join(p.read_text(encoding="utf-8", errors="replace") for p in site.rglob("*.html"))
    text = visible_text(site, run["lang"]).lower()

    row.update({
        "pages": len(pages),
        "axe_errors": sum(1 for f in findings if f["rule"].startswith("axe-") and f["level"] == "error"),
        "axe_warnings": sum(1 for f in findings if f["rule"].startswith("axe-") and f["level"] == "warning"),
        "overflow": sum(1 for f in findings if f["rule"] == "horizontal-overflow"),
        "console_errors": sum(1 for f in findings if f["rule"] == "console-error"),
        "cliche_hits": sum(text.count(phrase) for phrase in load_cliches(run["lang"])),
        "placeholders": len(re.findall(r"\[\[ISI:", html)),
    })
    report_file = site / ".ScaffolDev" / "report.json"
    if report_file.is_file():
        summary = io.read_json(report_file).get("summary", {})
        row.update({"check_errors": summary.get("errors", ""), "check_warnings": summary.get("warnings", "")})

    return row, render_check.site_fingerprint(results)


def dhi(fingerprints):
    """
    Design Homogeneity Index: kemiripan rata-rata antara situs untuk brief yang berbeda.

    I.S. : fingerprints adalah daftar (brief, sidik) dalam satu kondisi dan model.
    F.S. : Angka 0-1 dikembalikan (1 = semua situs sama), atau "" bila kurang dari dua brief.
           Kemiripan sepasang = rata-rata (1 - jarak tata letak) dan (1 - jarak warna / 50 ΔE).
    """
    scores = []
    for (brief_a, a), (brief_b, b) in itertools.combinations(fingerprints, 2):
        if brief_a == brief_b:
            continue
        color = min(metrics.color_distance(a["color"], b["color"]) / 50, 1)
        layout = metrics.layout_distance(a["layout"], b["layout"])
        scores.append(1 - (color + layout) / 2)
    return round(sum(scores) / len(scores), 3) if scores else ""


# ============================================================
# ========================== UTAMA ===========================
# ============================================================


def main():
    """
    Titik masuk CLI.

    I.S. : sys.argv berisi opsi harness.
    F.S. : Semua run dijalankan dan diukur; CSV ditulis; ringkasan per kondisi dikembalikan.
           --dry-run hanya mencetak rencana.
    """
    parser = argparse.ArgumentParser(description="Harness evaluasi C0/C1/C2.")
    parser.add_argument("--out", required=True, help="folder hasil (satu subfolder per run)")
    parser.add_argument("--models", required=True, help="daftar model dipisah koma, mis. sonnet,opus")
    parser.add_argument("--conditions", default="C0,C1,C2")
    parser.add_argument("--briefs", default=str(Path(__file__).with_name("briefs.yaml")))
    parser.add_argument("--only", help="id brief dipisah koma (bawaan: semua)")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--c1-plugin", help="folder plugin frontend-design Anthropic (wajib untuk C1)")
    parser.add_argument("--agent-command", default=CLAUDE)
    parser.add_argument("--budget", default="5", help="batas biaya per run dalam USD (Claude Code)")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--browser")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    if not set(conditions) <= set(CONDITIONS):
        fail(EXIT_INVALID, f"Kondisi tidak dikenal: {args.conditions}", "use C0, C1, and/or C2")
    if "C1" in conditions and not (args.c1_plugin and Path(args.c1_plugin).is_dir()):
        fail(EXIT_INVALID, "C1 butuh folder plugin frontend-design (--c1-plugin).",
             "pass --c1-plugin, or drop C1 from --conditions")

    briefs = yaml.safe_load(Path(args.briefs).read_text(encoding="utf-8"))["briefs"]
    if args.only:
        wanted = set(args.only.split(","))
        briefs = [b for b in briefs if b["id"] in wanted]
    runs = plan(briefs, conditions, [m.strip() for m in args.models.split(",")], args.reps)

    if args.dry_run:
        return [f"{len(runs)} run direncanakan:"] + [f"  - {r['run']}" for r in runs], "run again without --dry-run"

    out = Path(args.out).resolve()
    browser = render_check.find_browser(args.browser)
    rows, fingerprints = [], {}
    for run in runs:
        folder = out / run["run"]
        if (folder / "row.json").is_file():
            row, fingerprint = io.read_json(folder / "row.json"), io.read_json(folder / "fingerprint.json")
        else:
            code, seconds, used = run_agent(run, folder, args.agent_command, args.c1_plugin, args.budget, args.timeout)
            measured, fingerprint = measure(run, folder, find_site(folder), browser)
            row = {k: run[k] for k in ("run", "condition", "model", "brief", "lang", "rep")}
            row.update({"exit": code, "seconds": seconds, **used, **measured})
            io.write_json(folder / "row.json", row)
            io.write_json(folder / "fingerprint.json", fingerprint)
        rows.append(row)
        if fingerprint:
            fingerprints.setdefault((row["condition"], row["model"]), []).append((row["brief"], fingerprint))

    for row in rows:
        row["dhi"] = dhi(fingerprints.get((row["condition"], row["model"]), []))

    csv_path = out / "eval.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows({k: row.get(k, "") for k in COLUMNS} for row in rows)

    lines = [f"{len(rows)} run ditulis ke {csv_path}."]
    for (condition, model), group in sorted(fingerprints.items()):
        lines.append(f"  - {condition} {model}: DHI {dhi(group)} ({len(group)} situs)")
    return lines, "compare DHI between conditions; run tools/build_cliches.py on this folder"


if __name__ == "__main__":
    report.run(main)
