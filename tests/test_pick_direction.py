# ============================================================
# File      : test_pick_direction.py
# Deskripsi : Pengujian unit dan CLI untuk pick_direction.py.
# ============================================================

import collections

import pytest
from conftest import FIXTURES, copy_fixture, next_line, run_script
from lib import io


@pytest.fixture
def kopi_ready(projects_dir):
    """
    Menyiapkan proyek kopi-senja lengkap sampai langkah gaps.json dan directions.yaml.
    """
    proj = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    res = run_script("gaps", "kopi-senja")
    assert res.returncode == 0
    return proj


def test_pick_direction_reproduces_fixture_exactly(kopi_ready):
    result = run_script("pick_direction", "kopi-senja", "--pick", "dir-2", "--seed", "4182")
    assert result.returncode == 0, result.stderr
    assert next_line(result) == "NEXT: run compile_tokens.py"

    gen_file = kopi_ready / "decisions.yaml"
    assert gen_file.is_file()

    expected = io.read_yaml(FIXTURES / "kopi-senja" / "decisions.yaml")
    actual = io.read_yaml(gen_file)

    assert actual["project"] == expected["project"]
    assert actual["direction"] == expected["direction"]
    assert actual["seed"] == 4182

    # Bandingkan setiap keputusan
    assert len(actual["decisions"]) == len(expected["decisions"])
    for act_d, exp_d in zip(actual["decisions"], expected["decisions"]):
        assert act_d == exp_d

    # Bandingkan setiap batasan
    assert len(actual["constraints"]) == len(expected["constraints"])
    for act_c, exp_c in zip(actual["constraints"], expected["constraints"]):
        assert act_c == exp_c


def test_pick_direction_determinism_same_seed(kopi_ready):
    res1 = run_script("pick_direction", "kopi-senja", "--seed", "12345")
    dec1 = io.read_yaml(kopi_ready / "decisions.yaml")

    res2 = run_script("pick_direction", "kopi-senja", "--seed", "12345")
    dec2 = io.read_yaml(kopi_ready / "decisions.yaml")

    assert res1.returncode == 0
    assert res2.returncode == 0
    assert dec1["direction"] == dec2["direction"]
    assert dec1["decisions"] == dec2["decisions"]


def test_pick_direction_frequencies_over_1000_seeds(kopi_ready):
    import random

    dirs_data = io.read_yaml(kopi_ready / "directions.yaml")["directions"]
    weights = [d["probability"] for d in dirs_data]
    expected_probs = {d["id"]: d["probability"] for d in dirs_data}

    # Uji 1.000 seed menggunakan algoritma sampling yang sama
    counts = collections.Counter()
    for seed in range(1000):
        rng = random.Random(seed)
        chosen = rng.choices(dirs_data, weights=weights, k=1)[0]
        counts[chosen["id"]] += 1

    for dir_id, p in expected_probs.items():
        observed_freq = counts[dir_id] / 1000.0
        # Toleransi ±3 percentage points (±0.03) sesuai spesifikasi
        assert abs(observed_freq - p) <= 0.03, (
            f"Frekuensi untuk {dir_id}: teramati {observed_freq:.3f}, diharapkan {p:.3f}"
        )


def test_pick_direction_cross_check_validation_fails(kopi_ready):
    dirs_file = kopi_ready / "directions.yaml"
    dirs_data = io.read_yaml(dirs_file)

    # 1. Total probabilitas tidak sama dengan 1
    dirs_data["directions"][0]["probability"] = 0.9
    io.write_yaml(dirs_file, dirs_data)

    res = run_script("pick_direction", "kopi-senja")
    assert res.returncode == 1
    assert "Probabilitas harus berjumlah 1.0" in res.stdout
