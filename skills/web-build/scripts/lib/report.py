# ============================================================
# File      : report.py
# Deskripsi : Kode keluar bersama, ringkasan untuk manusia, dan baris
#             NEXT: yang dibaca agen di akhir setiap skrip.
# ============================================================

import sys

# ============================================================
# ======================== KODE KELUAR =======================
# ============================================================

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_CHECK_FAILED = 2
EXIT_ASK = 3
EXIT_TIMEOUT = 4


class ScriptExit(Exception):
    """
    Menghentikan skrip dengan kode keluar, pesan, dan langkah berikutnya.

    I.S. : Skrip menemukan kondisi yang harus dilaporkan.
    F.S. : run() menangkap exception ini, mencetak pesan dan NEXT:, lalu keluar.
    """

    def __init__(self, code, lines, next_step):
        """
        Menyimpan kode keluar, baris pesan, dan langkah berikutnya.

        I.S. : code adalah kode keluar; lines berupa string atau list string; next_step adalah teks
               untuk baris NEXT:.
        F.S. : Atribut code, lines (selalu list), dan next_step terisi.
        """
        super().__init__("\n".join(lines) if isinstance(lines, list) else lines)
        self.code = code
        self.lines = lines if isinstance(lines, list) else [lines]
        self.next_step = next_step


def fail(code, lines, next_step):
    """
    Melempar ScriptExit; dipakai agar pemanggil cukup satu baris.

    I.S. : Kondisi gagal sudah diketahui.
    F.S. : ScriptExit dilempar.
    """
    raise ScriptExit(code, lines, next_step)


# ============================================================
# ========================== KELUARAN ========================
# ============================================================


def setup_output():
    """
    Memaksa stdout dan stderr memakai UTF-8.

    I.S. : Konsol Windows mungkin memakai code page lama.
    F.S. : Karakter seperti em dash dan huruf beraksen tercetak tanpa error.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def emit(lines, next_step):
    """
    Mencetak ringkasan lalu satu baris NEXT: sebagai baris terakhir.

    I.S. : lines berupa list string (boleh kosong).
    F.S. : Ringkasan dan 'NEXT: <next_step>' tercetak di stdout.
    """
    for line in lines:
        print(line)

    print(f"NEXT: {next_step}")
    sys.stdout.flush()


def run(main):
    """
    Menjalankan fungsi main skrip dan mengubah hasilnya menjadi kode keluar.

    I.S. : main() mengembalikan (lines, next_step) atau melempar ScriptExit.
    F.S. : Keluaran tercetak; proses keluar dengan kode yang sesuai.
    """
    setup_output()

    try:
        lines, next_step = main()
    except ScriptExit as stop:
        emit(stop.lines, stop.next_step)
        sys.exit(stop.code)

    emit(lines, next_step)
    sys.exit(EXIT_OK)

