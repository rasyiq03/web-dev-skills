# ============================================================
# File      : color.py
# Deskripsi : Perhitungan rasio kontras WCAG 2.x, konversi OKLCH <-> sRGB,
#             penjepit gamut (gamut clamp), serta turunan warna grafik
#             dan status (positif, negatif, peringatan).
# ============================================================

import math
import re

HEX_PATTERN = re.compile(r"^#?([0-9a-fA-F]{6})$")


# ============================================================
# ========================== WCAG 2.x ========================
# ============================================================


def hex_to_rgb(hex_code):
    """
    Mengonversi string heksadesimal #RRGGBB ke tuple (r, g, b) dalam rentang [0, 1].

    I.S. : hex_code berupa string '#RRGGBB' atau 'RRGGBB'.
    F.S. : Tuple (r, g, b) float dikembalikan.
    """
    match = HEX_PATTERN.match(hex_code.strip())
    if not match:
        raise ValueError(f"Format hex tidak sah: {hex_code}")
    raw = match.group(1)
    r = int(raw[0:2], 16) / 255.0
    g = int(raw[2:4], 16) / 255.0
    b = int(raw[4:6], 16) / 255.0
    return r, g, b


def rgb_to_hex(r, g, b):
    """
    Mengonversi komponen (r, g, b) dalam rentang [0, 1] ke string '#RRGGBB'.

    I.S. : r, g, b float, dijepit ke [0, 1].
    F.S. : String heksadesimal huruf kapital dikembalikan.
    """
    r_byte = max(0, min(255, round(r * 255)))
    g_byte = max(0, min(255, round(g * 255)))
    b_byte = max(0, min(255, round(b * 255)))
    return f"#{r_byte:02X}{g_byte:02X}{b_byte:02X}"


def srgb_to_linear(c):
    """
    Melinearkan satu saluran sRGB sesuai spesifikasi IEC 61966-2-1.

    I.S. : c dalam [0, 1].
    F.S. : Nilai linear dikembalikan.
    """
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    """
    Menerapkan kurva gamma sRGB dari nilai linear.

    I.S. : c nilai linear.
    F.S. : Nilai sRGB non-linear dalam [0, 1] dikembalikan.
    """
    if c <= 0.0031308:
        return max(0.0, 12.92 * c)
    return max(0.0, min(1.0, 1.055 * (c ** (1.0 / 2.4)) - 0.055))


def relative_luminance(hex_code):
    """
    Menghitung relative luminance (L) WCAG 2.x untuk warna hex.

    I.S. : hex_code string #RRGGBB.
    F.S. : Float L dalam rentang [0, 1] dikembalikan.
    """
    r, g, b = hex_to_rgb(hex_code)
    r_lin = srgb_to_linear(r)
    g_lin = srgb_to_linear(g)
    b_lin = srgb_to_linear(b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(hex1, hex2):
    """
    Menghitung rasio kontras WCAG 2.x antara dua warna hex.

    I.S. : hex1 dan hex2 adalah string warna #RRGGBB.
    F.S. : Nilai rasio (>= 1.0) dikembalikan, dibulatkan ke 2 desimal.
    """
    l1 = relative_luminance(hex1)
    l2 = relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    ratio = (lighter + 0.05) / (darker + 0.05)
    return round(ratio, 2)


# ============================================================
# ======================== OKLCH <-> sRGB ====================
# ============================================================


def hex_to_oklch(hex_code):
    """
    Mengonversi warna hex ke OKLCH (L, C, h).

    I.S. : hex_code #RRGGBB.
    F.S. : (L, C, h) dengan L dalam [0, 1], C >= 0, h dalam derajat [0, 360).
    """
    r, g, b = hex_to_rgb(hex_code)
    r_lin = srgb_to_linear(r)
    g_lin = srgb_to_linear(g)
    b_lin = srgb_to_linear(b)

    # linear sRGB ke LMS
    l = 0.4122214708 * r_lin + 0.5363325363 * g_lin + 0.0514459929 * b_lin
    m = 0.2119034982 * r_lin + 0.6806995451 * g_lin + 0.1073969566 * b_lin
    s = 0.0883024619 * r_lin + 0.2817188376 * g_lin + 0.6299787005 * b_lin

    l_ = math.cbrt(l) if l > 0 else 0.0
    m_ = math.cbrt(m) if m > 0 else 0.0
    s_ = math.cbrt(s) if s > 0 else 0.0

    # LMS ke OKLab
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b_coord = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    C = math.hypot(a, b_coord)
    h = math.degrees(math.atan2(b_coord, a)) % 360.0

    return L, C, h


def oklch_to_linear_rgb(L, C, h):
    """
    Mengonversi OKLCH ke komponen RGB linear (bisa di luar [0, 1]).

    I.S. : L dalam [0, 1], C >= 0, h derajat.
    F.S. : (r_lin, g_lin, b_lin) float.
    """
    h_rad = math.radians(h)
    a = C * math.cos(h_rad)
    b_coord = C * math.sin(h_rad)

    l_ = L + 0.3963377774 * a + 0.2158037573 * b_coord
    m_ = L - 0.1055613458 * a - 0.0638541728 * b_coord
    s_ = L - 0.0894841775 * a - 1.2914855480 * b_coord

    l = l_ ** 3
    m = m_ ** 3
    s = s_ ** 3

    r_lin = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g_lin = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b_lin = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    return r_lin, g_lin, b_lin


def is_in_srgb_gamut(r_lin, g_lin, b_lin, tol=0.0005):
    """
    Memeriksa apakah komponen RGB linear berada dalam gamut sRGB.

    I.S. : r_lin, g_lin, b_lin float.
    F.S. : True bila semua dalam rentang [-tol, 1 + tol].
    """
    return (
        -tol <= r_lin <= 1.0 + tol
        and -tol <= g_lin <= 1.0 + tol
        and -tol <= b_lin <= 1.0 + tol
    )


def oklch_to_hex(L, C, h):
    """
    Mengonversi OKLCH ke #RRGGBB dengan penjepitan kroma ke gamut sRGB.

    I.S. : L dalam [0, 1], C >= 0, h derajat.
    F.S. : Hex string dalam gamut sRGB dengan L dan h dipertahankan.
    """
    # Binary search kroma agar muat di sRGB gamut
    low_c = 0.0
    high_c = C
    best_c = 0.0

    for _ in range(20):
        mid_c = (low_c + high_c) / 2.0
        r_lin, g_lin, b_lin = oklch_to_linear_rgb(L, mid_c, h)
        if is_in_srgb_gamut(r_lin, g_lin, b_lin):
            best_c = mid_c
            low_c = mid_c
        else:
            high_c = mid_c

    r_lin, g_lin, b_lin = oklch_to_linear_rgb(L, best_c, h)
    r = linear_to_srgb(r_lin)
    g = linear_to_srgb(g_lin)
    b = linear_to_srgb(b_lin)

    return rgb_to_hex(r, g, b)


# ============================================================
# =================== WARNA GRAFIK & STATUS ==================
# ============================================================


def derive_chart_color(accent_hex, paper_hex, hue_offset):
    """
    Membuat warna grafik (chart-2..6) dengan merotasi hue aksen dan
    memilih lightness terdekat yang mencapai kontras >= 3.0 terhadap paper.

    I.S. : accent_hex dan paper_hex sah; hue_offset kelipatan 60 derajat.
    F.S. : Hex string warna grafik dikembalikan.
    """
    acc_l, acc_c, acc_h = hex_to_oklch(accent_hex)
    target_h = (acc_h + hue_offset) % 360.0

    # Cek lightness asli terlebih dahulu
    candidate_hex = oklch_to_hex(acc_l, acc_c, target_h)
    if contrast_ratio(candidate_hex, paper_hex) >= 3.0:
        return candidate_hex

    # Cari L terdekat dengan acc_l yang mencapai kontras >= 3.0
    best_hex = candidate_hex
    min_dist = float("inf")

    # Evaluasi grid lightness 0.05 .. 0.95
    for step in range(5, 96, 2):
        l_val = step / 100.0
        c_hex = oklch_to_hex(l_val, acc_c, target_h)
        ratio = contrast_ratio(c_hex, paper_hex)
        if ratio >= 3.0:
            dist = abs(l_val - acc_l)
            if dist < min_dist:
                min_dist = dist
                best_hex = c_hex

    return best_hex


def derive_state_color(target_hue, paper_hex):
    """
    Membuat warna status (positive 145°, negative 25°, warning 80°)
    dengan lightness yang mencapai kontras >= 4.5 terhadap paper.

    I.S. : target_hue dalam derajat, paper_hex sah.
    F.S. : Hex string warna status dikembalikan.
    """
    chroma = 0.16
    paper_l = relative_luminance(paper_hex)

    # Bila background terang (paper_l > 0.3), arahkan L ke gelap; sebaliknya ke terang
    l_candidates = [x / 100.0 for x in range(15, 95, 2)]
    if paper_l > 0.3:
        l_candidates.sort()  # Coba yang gelap dulu
    else:
        l_candidates.sort(reverse=True)  # Coba yang terang dulu

    for l_val in l_candidates:
        c_hex = oklch_to_hex(l_val, chroma, target_hue)
        if contrast_ratio(c_hex, paper_hex) >= 4.5:
            return c_hex

    # Fallback aman
    return "#1B5E20" if target_hue > 100 else ("#B71C1C" if target_hue < 50 else "#E65100")
