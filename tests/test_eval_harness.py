# ============================================================
# File      : test_eval_harness.py
# Deskripsi : Pengujian tools/eval/harness.py dengan agen tiruan: rencana
#             run, pembacaan token, pengukuran situs di browser, DHI, dan
#             meta.json yang dipakai build_cliches.
# ============================================================

import csv
import json
import sys

import pytest
from conftest import REPO, run_script

sys.path.insert(0, str(REPO / "tools" / "eval"))

import harness  # noqa: E402

FAKE_AGENT = '''
import json, pathlib, sys
prompt, model = sys.argv[1], sys.argv[2]
site = pathlib.Path("site")
site.mkdir()
color = "#fbf5ea" if "kopi" in prompt else "#10213a"
text = "#2b1e12" if "kopi" in prompt else "#ffffff"
site.joinpath("index.html").write_text(
    f'<!doctype html><html lang="id"><head><title>Uji</title></head>'
    f'<body style="background:{color};color:{text}"><header><h1>{prompt[:20]}</h1></header>'
    f'<main><section><h2>Solusi terbaik untuk Anda</h2><p>[[ISI: harga]]</p></section></main></body></html>',
    encoding="utf-8")
print(json.dumps({"usage": {"input_tokens": 100, "cache_read_input_tokens": 50, "output_tokens": 20},
                  "total_cost_usd": 0.01}))
'''


def test_plan_covers_every_combination_in_a_stable_order():
    briefs = [{"id": "a", "lang": "id", "prompt": "p"}, {"id": "b", "lang": "en", "prompt": "q"}]
    runs = harness.plan(briefs, ["C0", "C2"], ["sonnet"], 2)

    assert len(runs) == 8
    assert runs[0]["run"] == "C0-sonnet-a-1" and runs[-1]["run"] == "C2-sonnet-b-2"


def test_usage_reads_tokens_and_cost_from_agent_json():
    out = json.dumps({"usage": {"input_tokens": 10, "cache_creation_input_tokens": 5, "output_tokens": 3},
                      "total_cost_usd": 0.2})

    assert harness.usage(out) == {"input_tokens": 15, "output_tokens": 3, "cost_usd": 0.2}
    assert harness.usage("not json")["cost_usd"] == ""


def test_c1_needs_its_plugin(tmp_path):
    result = run_script("harness", "--out", str(tmp_path), "--models", "x", "--conditions", "C1",
                        script_dir=REPO / "tools" / "eval")

    assert result.returncode == 1
    assert "--c1-plugin" in result.stdout


@pytest.mark.network
def test_harness_runs_measures_and_writes_csv(tmp_path):
    try:
        sys.path.insert(0, str(REPO / "tools"))
        import render_check
        render_check.find_browser()
    except Exception:
        pytest.skip("Chrome atau Chromium tidak terpasang")

    agent = tmp_path / "fake_agent.py"
    agent.write_text(FAKE_AGENT, encoding="utf-8")
    briefs = tmp_path / "briefs.yaml"
    briefs.write_text("briefs:\n  - {id: kopi, lang: id, prompt: kopi di Bandung}\n"
                      "  - {id: klinik, lang: id, prompt: klinik di Surabaya}\n", encoding="utf-8")
    out = tmp_path / "out"

    result = run_script("harness", "--out", str(out), "--models", "fake", "--conditions", "C0", "--reps", "1",
                        "--briefs", str(briefs), "--agent-command", f"{sys.executable} {agent} {{prompt}} {{model}}",
                        script_dir=REPO / "tools" / "eval")

    assert result.returncode == 0, result.stdout + result.stderr
    rows = list(csv.DictReader((out / "eval.csv").open(encoding="utf-8")))
    assert [r["brief"] for r in rows] == ["kopi", "klinik"]
    assert rows[0]["input_tokens"] == "150" and rows[0]["cost_usd"] == "0.01"
    assert rows[0]["pages"] == "1" and rows[0]["placeholders"] == "1"
    # Dua situs dengan struktur sama tetapi warna berlawanan: DHI di antara 0 dan 1
    assert 0 < float(rows[0]["dhi"]) < 1
    meta = json.loads((out / "C0-fake-kopi-1" / "meta.json").read_text(encoding="utf-8"))
    assert meta == {"model": "fake", "brief": "kopi", "condition": "C0", "site": "site"}

    # Dijalankan ulang: run yang sudah diukur tidak diulang
    again = run_script("harness", "--out", str(out), "--models", "fake", "--conditions", "C0", "--reps", "1",
                       "--briefs", str(briefs), "--agent-command", "false", script_dir=REPO / "tools" / "eval")
    assert again.returncode == 0
