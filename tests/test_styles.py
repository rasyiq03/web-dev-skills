# ============================================================
# File      : test_styles.py
# Deskripsi : Pengujian pustaka gaya dan heuristik layout: setiap gaya di
#             katalog lengkap dan lolos kontras, tidak memakai font yang
#             dilarang audit, bisa disusun menjadi token; pola dengan needs
#             yang belum ada di brief diperingatkan di pick, context, decide.
# ============================================================

import re

import pytest
import yaml
from conftest import REPO, copy_fixture, run_script

from lib import color, io, project

STYLES_DIR = REPO / "skills" / "web-design" / "styles"
INDEX = yaml.safe_load((STYLES_DIR / "index.yaml").read_text(encoding="utf-8"))["styles"]
BANNED = re.search(r"\\b\((.+?)\)\\b", next(
    r["pattern"] for r in yaml.safe_load((REPO / "audit" / "anti-slop.yaml").read_text(encoding="utf-8"))["rules"]
    if r["id"] == "default-font")).group(1).split("|")


def load(entry):
    return yaml.safe_load((STYLES_DIR / entry["file"]).read_text(encoding="utf-8"))


@pytest.mark.parametrize("entry", INDEX, ids=[e["id"] for e in INDEX])
def test_style_is_complete_and_consistent_with_catalog(entry):
    style = load(entry)

    assert style["id"] == entry["id"]
    assert style["formality"] == entry["formality"] in ("casual", "neutral", "formal")
    assert style["suits"] and style["avoid"] and entry["fits"]
    assert set(style["base"]) >= {"type_scale", "space", "radius", "border", "shadow", "motion"}
    assert set(style["components"]) >= {"button", "card", "section", "label", "image"}
    assert len(style["palettes"]) >= 3 and len(style["pairings"]) >= 3
    assert len(style["signature_moves"]) >= 2


@pytest.mark.parametrize("entry", INDEX, ids=[e["id"] for e in INDEX])
def test_every_palette_passes_contrast(entry):
    for palette in load(entry)["palettes"]:
        c = palette["colors"]

        assert color.contrast_ratio(c["ink"], c["paper"]) >= 4.5, palette["id"]
        assert color.contrast_ratio(c["muted"], c["paper"]) >= 4.5, palette["id"]
        assert color.contrast_ratio(c["accent-ink"], c["accent"]) >= 4.5, palette["id"]


@pytest.mark.parametrize("style_id", ["clean-swiss", "soft-organic", "data-utility"])
def test_new_styles_keep_the_accent_visible_on_paper(style_id):
    for palette in load(next(e for e in INDEX if e["id"] == style_id))["palettes"]:
        c = palette["colors"]
        assert color.contrast_ratio(c["accent"], c["paper"]) >= 3.0, palette["id"]


@pytest.mark.parametrize("palette, expected", [("warm-paper", "#1B1A17"), ("mint-signal", "#2B59C3")])
def test_link_token_falls_back_to_ink_when_accent_is_faint(projects_dir, palette, expected):
    work = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    assert run_script("gaps", "kopi-senja").returncode == 0
    assert run_script("pick_direction", "kopi-senja", "--pick", "dir-2").returncode == 0

    assert run_script("compile_tokens", "kopi-senja").returncode == 0

    if palette != "warm-paper":
        assert run_script("decide", "kopi-senja", "d-palette-1", "--choice", palette,
                          "--reason", "Uji warna tautan yang terbaca.").returncode == 0

    assert f"--pd-color-link: {expected};" in (work / "tokens.css").read_text(encoding="utf-8")


@pytest.mark.parametrize("entry", INDEX, ids=[e["id"] for e in INDEX])
def test_no_pairing_uses_a_font_the_audit_bans(entry):
    for pairing in load(entry)["pairings"]:
        for role in ("display", "body", "mono"):
            name = pairing[role].lower()
            assert not any(re.search(rf"\b{banned}\b", name) for banned in BANNED), f"{pairing['id']}: {pairing[role]}"


def test_catalog_lists_every_style_file():
    files = {p.name for p in STYLES_DIR.glob("*.yaml")} - {"index.yaml", "_template.yaml"}

    assert {e["file"] for e in INDEX} == files
    assert len({e["formality"] for e in INDEX}) == 3


def direction(n, style, palette, pairing, motion, tone, probability):
    return {
        "id": f"dir-{n}", "probability": probability, "style": style, "palette": palette, "type_pairing": pairing,
        "layout": {"hero": "full-bleed-type", "services": "list-with-prices", "proof": "facts-ledger",
                   "story": "two-column-narrative", "contact": "contact-card"},
        "motion": motion, "tone": tone, "register": {"id": "Anda"}, "summary": "Uji gaya baru.",
        "rationale": {k: "Cocok untuk mahasiswa di Bandung yang membuka situs di HP." for k in
                      ("style", "color", "typography", "layout", "motion", "tone")},
        "based_on": ["req-audience"],
    }


@pytest.mark.parametrize("style_id", ["clean-swiss", "soft-organic", "data-utility"])
def test_new_styles_compile_into_tokens(projects_dir, style_id):
    work = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml"])
    style = load(next(e for e in INDEX if e["id"] == style_id))
    others = [("neobrutalism", "warm-paper", "grotesk-mono"), ("editorial", "ink-on-cream", "fraunces-plex"),
              ("neobrutalism", "sun-block", "wide-display"), ("neobrutalism", "mint-signal", "bricolage-plex")]
    dirs = [direction(1, style_id, style["palettes"][0]["id"], style["pairings"][0]["id"], "none", "tenang", 0.4)]
    dirs += [direction(i + 2, *o, ["low", "medium", "none", "low"][i], f"nada-{i}", 0.15) for i, o in enumerate(others)]
    io.write_yaml(work / "directions.yaml", {"directions": dirs})

    for args in (("gaps",), ("pick_direction", "--pick", "dir-1"), ("compile_tokens",)):
        result = run_script(args[0], "kopi-senja", *args[1:])
        assert result.returncode == 0, result.stdout

    assert style["palettes"][0]["colors"]["accent"] in (work / "tokens.css").read_text(encoding="utf-8")


# ============================================================
# ===================== HEURISTIK LAYOUT =====================
# ============================================================


def test_layout_risks_follow_the_brief():
    site_type = project.load_site_type("company-profile")
    layout = {"hero": "split-offset", "proof": "single-quote", "contact": "contact-card"}
    unknown = {"assets": {"photos": {"value": "unknown", "source": "unknown"}}}
    stated = {"assets": {"photos": {"value": "foto kedai", "source": "stated"}},
              "facts": {"testimonials": {"value": "Enak!", "source": "stated"}}}

    assert project.layout_risks(unknown, site_type, layout) == [
        ("hero", "split-offset", ["assets.photos"]), ("proof", "single-quote", ["facts.testimonials"])]
    assert project.layout_risks(stated, site_type, layout) == []


def test_pick_and_context_warn_about_missing_photos(projects_dir):
    work = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    assert run_script("gaps", "kopi-senja").returncode == 0

    picked = run_script("pick_direction", "kopi-senja", "--pick", "dir-2")
    assert "Peringatan: hero=split-offset butuh assets.photos" in picked.stdout

    context = run_script("context", "kopi-senja", "index")
    assert "risk | hero | split-offset needs assets.photos (unknown)" in context.stdout
    assert "risk |" not in run_script("context", "kopi-senja", "kontak").stdout


def test_flat_probabilities_are_flagged(projects_dir):
    work = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])
    data = io.read_yaml(work / "directions.yaml")

    for d in data["directions"]:
        d["probability"] = 0.2
    io.write_yaml(work / "directions.yaml", data)
    assert run_script("gaps", "kopi-senja").returncode == 0

    assert "kelima peluang hampir sama" in run_script("pick_direction", "kopi-senja", "--pick", "dir-1").stdout


def test_decide_warns_when_new_pattern_lacks_facts(projects_dir):
    work = copy_fixture(projects_dir, "kopi-senja", ["brief.yaml", "directions.yaml"])

    for args in (("gaps",), ("pick_direction", "--pick", "dir-2")):
        assert run_script(args[0], "kopi-senja", *args[1:]).returncode == 0

    result = run_script("decide", "kopi-senja", "d-layout-1", "--section", "proof", "--choice", "logo-strip-plain",
                        "--reason", "Klien ingin menampilkan nama pelanggan korporat.")

    assert result.returncode == 0, result.stdout
    assert "peringatan: proof=logo-strip-plain butuh facts.client_names" in result.stdout
