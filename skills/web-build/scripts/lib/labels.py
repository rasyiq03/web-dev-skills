# ============================================================
# File      : labels.py
# Deskripsi : Label manusia untuk setiap fakta di tipe situs, dalam
#             bahasa Indonesia dan Inggris, untuk placeholder [[ISI: ...]].
# ============================================================

# ============================================================
# ========================== LABEL ===========================
# ============================================================

FACT_LABELS = {
    # company-profile
    "address": {"id": "alamat", "en": "address"},
    "whatsapp": {"id": "nomor WhatsApp", "en": "WhatsApp number"},
    "email": {"id": "alamat email", "en": "email address"},
    "hours": {"id": "jam buka", "en": "opening hours"},
    "services": {"id": "daftar layanan atau menu", "en": "list of services or products"},
    "founded_year": {"id": "tahun berdiri", "en": "year founded"},
    "client_names": {"id": "nama klien", "en": "client names"},
    "team_members": {"id": "nama dan peran tim", "en": "team names and roles"},
    # dashboard
    "data_source": {"id": "sumber data", "en": "data source"},
    "metrics": {"id": "metrik utama", "en": "key metrics"},
    "entities": {"id": "jenis data yang dicatat", "en": "record types"},
    "time_range": {"id": "rentang waktu bawaan", "en": "default time range"},
    "user_roles": {"id": "peran pengguna", "en": "user roles"},
    # landing
    "product_name": {"id": "nama produk", "en": "product name"},
    "price": {"id": "harga", "en": "price"},
    "features": {"id": "fitur utama", "en": "key features"},
    "signup_url": {"id": "tautan pendaftaran", "en": "sign-up link"},
    "deadline": {"id": "batas waktu", "en": "deadline"},
    # portfolio
    "projects": {"id": "daftar proyek", "en": "list of projects"},
    "skills": {"id": "keahlian", "en": "skills"},
    "social_links": {"id": "tautan media sosial", "en": "social media links"},
    "cv_url": {"id": "tautan CV", "en": "CV link"},
    # umkm-catalog
    "products": {"id": "daftar produk", "en": "list of products"},
    "prices": {"id": "harga produk", "en": "product prices"},
    "marketplace_links": {"id": "tautan marketplace", "en": "marketplace links"},
    "shipping_area": {"id": "area pengiriman", "en": "shipping area"},
}


# ============================================================
# ========================== FUNGSI ==========================
# ============================================================


def fact_label(fact, lang):
    """
    Mengambil label satu fakta dalam satu bahasa.

    I.S. : fact adalah nama fakta snake_case; lang adalah 'id' atau 'en'.
    F.S. : Label dikembalikan; fakta tak dikenal memakai namanya dengan '_' diganti spasi.
    """
    labels = FACT_LABELS.get(fact)

    if not labels:
        return fact.replace("_", " ")

    return labels.get(lang) or labels["id"]


def placeholder(fact, lang):
    """
    Membuat placeholder untuk fakta yang belum diketahui.

    I.S. : fact dan lang seperti pada fact_label.
    F.S. : String '[[ISI: <label>]]' dikembalikan.
    """
    return f"[[ISI: {fact_label(fact, lang)}]]"

