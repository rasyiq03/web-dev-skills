# ============================================================
# File      : test_color.py
# Deskripsi : Pengujian unit algoritma WCAG, OKLCH, dan penurunan warna di lib/color.py.
# ============================================================

import pytest
from lib import color


def test_wcag_contrast_black_and_white():
    # Hitam (#000000) dan putih (#FFFFFF) rasio kontras 21:1
    ratio = color.contrast_ratio("#000000", "#FFFFFF")
    assert ratio == 21.0


def test_wcag_contrast_same_color():
    ratio = color.contrast_ratio("#F4EBDD", "#F4EBDD")
    assert ratio == 1.0


def test_wcag_kopi_senja_contrast():
    # Warm-paper palette:
    # ink: #1B1A17, paper: #F4EBDD, accent: #F26B3A, muted: #5E574D, accent-ink: #1B1A17
    ratio_body = color.contrast_ratio("#1B1A17", "#F4EBDD")
    assert ratio_body >= 4.5

    ratio_muted = color.contrast_ratio("#5E574D", "#F4EBDD")
    assert ratio_muted >= 4.5

    ratio_accent = color.contrast_ratio("#1B1A17", "#F26B3A")
    assert ratio_accent >= 4.5


def test_oklch_roundtrip():
    hex_in = "#F26B3A"
    L, C, h = color.hex_to_oklch(hex_in)
    hex_out = color.oklch_to_hex(L, C, h)
    # Harus sangat dekat dengan input asli
    r1, g1, b1 = color.hex_to_rgb(hex_in)
    r2, g2, b2 = color.hex_to_rgb(hex_out)
    assert abs(r1 - r2) < 0.02
    assert abs(g1 - g2) < 0.02
    assert abs(b1 - b2) < 0.02


def test_derive_chart_and_state_colors():
    accent = "#F26B3A"
    paper = "#F4EBDD"

    # chart-2..6
    for offset in [60, 120, 180, 240, 300]:
        c_hex = color.derive_chart_color(accent, paper, offset)
        assert color.contrast_ratio(c_hex, paper) >= 3.0

    # positive, negative, warning
    for hue in [145, 25, 80]:
        st_hex = color.derive_state_color(hue, paper)
        assert color.contrast_ratio(st_hex, paper) >= 4.5
