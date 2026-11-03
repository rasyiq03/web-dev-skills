# ============================================================
# File      : metrics.py
# Proyek    : ScaffolDev
# Deskripsi : Ukuran kemiripan dua situs untuk render_check dan harness
#             evaluasi: jarak warna (Earth Mover's Distance antara
#             histogram CIELab) dan jarak tata letak (tree edit distance
#             Zhang-Shasha atas pohon landmark DOM). Pustaka standar saja.
# ============================================================

import heapq
import math
from collections import Counter

# ============================================================
# =========================== WARNA ==========================
# ============================================================

BIN = 12  # lebar satu sel histogram dalam satuan Lab
TOP_BINS = 12  # sel terbanyak yang dipakai; sisanya digabung ke sel terdekat
UNITS = 1000  # massa total histogram untuk aliran biaya minimum


def rgb_to_lab(r, g, b):
    """
    Mengonversi sRGB 0-255 ke CIELab (D65).

    I.S. : r, g, b dalam 0-255.
    F.S. : Tuple (L, a, b) dikembalikan.
    """
    def linear(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    rl, gl, bl = linear(r), linear(g), linear(b)
    x = (0.4124 * rl + 0.3576 * gl + 0.1805 * bl) / 0.95047
    y = 0.2126 * rl + 0.7152 * gl + 0.0722 * bl
    z = (0.0193 * rl + 0.1192 * gl + 0.9505 * bl) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def color_histogram(samples):
    """
    Menyusun histogram warna dari sampel [r, g, b, bobot].

    I.S. : samples adalah daftar sampel warna halaman (boleh dari beberapa halaman).
    F.S. : Daftar (pusat_lab, bobot) paling banyak TOP_BINS sel, bobot berjumlah 1.
    """
    bins = Counter()
    for r, g, b, weight in samples:
        lab = rgb_to_lab(r, g, b)
        bins[tuple(round(v / BIN) for v in lab)] += weight

    total = sum(bins.values()) or 1
    top = [cell for cell, _ in bins.most_common(TOP_BINS)]
    merged = Counter()
    for cell, weight in bins.items():
        nearest = min(top, key=lambda t: sum((a - b) ** 2 for a, b in zip(cell, t)))
        merged[nearest] += weight

    return [(tuple(v * BIN for v in cell), merged[cell] / total) for cell in sorted(merged)]


def _min_cost_flow(supply, demand, cost):
    """
    Menyelesaikan masalah transportasi kecil dengan aliran biaya minimum (Dijkstra + potensial).

    I.S. : supply dan demand berupa bilangan bulat dengan jumlah sama; cost matriks biaya.
    F.S. : Biaya total pengiriman minimum dikembalikan.
    """
    n, m = len(supply), len(demand)
    source, sink, size = n + m, n + m + 1, n + m + 2
    graph = [[] for _ in range(size)]

    def add(u, v, cap, c):
        graph[u].append([v, cap, c, len(graph[v])])
        graph[v].append([u, 0, -c, len(graph[u]) - 1])

    for i, s in enumerate(supply):
        add(source, i, s, 0)
    for j, d in enumerate(demand):
        add(n + j, sink, d, 0)
    for i in range(n):
        for j in range(m):
            add(i, n + j, min(supply[i], demand[j]), cost[i][j])

    total_cost, flow, need = 0.0, 0, sum(supply)
    potential = [0.0] * size
    while flow < need:
        dist, prev = [math.inf] * size, [None] * size
        dist[source] = 0.0
        queue = [(0.0, source)]
        while queue:
            d, u = heapq.heappop(queue)
            if d > dist[u]:
                continue
            for index, (v, cap, c, _) in enumerate(graph[u]):
                nd = d + c + potential[u] - potential[v]
                if cap > 0 and nd < dist[v] - 1e-12:
                    dist[v], prev[v] = nd, (u, index)
                    heapq.heappush(queue, (nd, v))
        if dist[sink] == math.inf:
            break
        potential = [p + (dist[i] if dist[i] < math.inf else 0) for i, p in enumerate(potential)]
        push, v = need - flow, sink
        while v != source:
            u, index = prev[v]
            push = min(push, graph[u][index][1])
            v = u
        v = sink
        while v != source:
            u, index = prev[v]
            edge = graph[u][index]
            edge[1] -= push
            graph[v][edge[3]][1] += push
            total_cost += push * edge[2]
            v = u
        flow += push

    return total_cost


def color_distance(hist_a, hist_b):
    """
    Earth Mover's Distance antara dua histogram warna, dalam satuan ΔE (CIE76).

    I.S. : Keduanya hasil color_histogram().
    F.S. : Jarak >= 0 dikembalikan; 0 berarti warna tersebar sama persis.
    """
    def units(hist):
        raw = [round(weight * UNITS) for _, weight in hist]
        raw[raw.index(max(raw))] += UNITS - sum(raw)
        return raw

    cost = [[math.dist(ca, cb) for cb, _ in hist_b] for ca, _ in hist_a]
    return round(_min_cost_flow(units(hist_a), units(hist_b), cost) / UNITS, 2)


# ============================================================
# ========================= TATA LETAK =======================
# ============================================================


def _postorder(tree):
    """
    Meratakan pohon [label, anak] menjadi label pascaurut dan daun paling kiri tiap simpul.

    I.S. : tree adalah daftar simpul [label, anak] (hutan); akar buatan ditambahkan.
    F.S. : (labels, leftmost) dikembalikan, indeks mulai 0.
    """
    labels, leftmost = [], []

    def visit(label, children):
        first = None
        for child_label, grandchildren in children:
            index = visit(child_label, grandchildren)
            first = leftmost[index] if first is None else first
        labels.append(label)
        leftmost.append(len(labels) - 1 if first is None else first)
        return len(labels) - 1

    visit("root", tree)
    return labels, leftmost


def tree_edit_distance(tree_a, tree_b):
    """
    Zhang-Shasha: jumlah sisip, hapus, dan ganti label minimum antara dua pohon.

    I.S. : Keduanya pohon landmark dari render.mjs.
    F.S. : Jarak bilangan bulat dikembalikan.
    """
    la, ma = _postorder(tree_a)
    lb, mb = _postorder(tree_b)
    keyroots_a = sorted({max(i for i in range(len(la)) if ma[i] == ma[k]) for k in range(len(la))})
    keyroots_b = sorted({max(j for j in range(len(lb)) if mb[j] == mb[k]) for k in range(len(lb))})
    td = [[0] * len(lb) for _ in la]

    for i in keyroots_a:
        for j in keyroots_b:
            rows, cols = i - ma[i] + 2, j - mb[j] + 2
            fd = [[0] * cols for _ in range(rows)]
            for x in range(1, rows):
                fd[x][0] = fd[x - 1][0] + 1
            for y in range(1, cols):
                fd[0][y] = fd[0][y - 1] + 1
            for x in range(1, rows):
                for y in range(1, cols):
                    i1, j1 = ma[i] + x - 1, mb[j] + y - 1
                    if ma[i1] == ma[i] and mb[j1] == mb[j]:
                        fd[x][y] = min(fd[x - 1][y] + 1, fd[x][y - 1] + 1,
                                       fd[x - 1][y - 1] + (la[i1] != lb[j1]))
                        td[i1][j1] = fd[x][y]
                    else:
                        fd[x][y] = min(fd[x - 1][y] + 1, fd[x][y - 1] + 1,
                                       fd[ma[i1] - ma[i]][mb[j1] - mb[j]] + td[i1][j1])
    return td[-1][-1]


def layout_distance(tree_a, tree_b):
    """
    Tree edit distance dinormalkan ke 0-1 dengan ukuran pohon yang lebih besar.

    I.S. : Keduanya pohon landmark.
    F.S. : 0 berarti struktur sama; 1 berarti berbeda seluruhnya.
    """
    size = max(len(_postorder(tree_a)[0]), len(_postorder(tree_b)[0]))
    return round(tree_edit_distance(tree_a, tree_b) / size, 3)
