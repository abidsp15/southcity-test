import re

# Tabel yang boleh diakses tiap role
ROLE_TABLES = {
    "Sales_Staff": ["Units", "Sales_Contracts", "Invoices_Billing"],
    "Management": ["Units", "Sales_Contracts", "Invoices_Billing", "GL_Journals"],
}

ALL_TABLES = ["Units", "Sales_Contracts", "Invoices_Billing", "GL_Journals"]

# Perintah SQL yang mengubah data -> selalu ditolak
FORBIDDEN_SQL = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE",
    "MERGE", "EXEC", "EXECUTE", "GRANT", "REVOKE", "ATTACH", "PRAGMA",
]

# Tabel sistem yang tidak boleh diintip
SYSTEM_TABLES = ["sqlite_master", "sqlite_schema", "information_schema", "sys."]

# Kata di pertanyaan yang artinya user ingin mengubah data
MODIFY_WORDS = [
    "hapus", "menghapus", "dihapus", "delete", "drop", "update", "ubah",
    "mengubah", "diubah", "insert", "alter", "truncate",
]

# Kalimat yang biasa dipakai untuk prompt injection
INJECTION_PHRASES = [
    "abaikan instruksi", "abaikan perintah", "lupakan instruksi",
    "ignore previous", "ignore all previous", "ignore the above",
]

# Kata yang menandakan pertanyaan butuh data jurnal (GL_Journals)
GL_WORDS = [
    "gl_journals", "jurnal", "journal", "general ledger", "buku besar",
    "kas & bank", "kas dan bank",
]


class AccessDenied(Exception):
    """Dipakai kalau permintaan harus ditolak."""


def check_role(role):
    if role not in ROLE_TABLES:
        raise AccessDenied(
            f"Role '{role}' tidak dikenal. Gunakan Sales_Staff atau Management."
        )


def check_question(question, role):
    """Cek pertanyaan SEBELUM dikirim ke AI."""
    text = question.lower()

    for phrase in INJECTION_PHRASES:
        if phrase in text:
            raise AccessDenied(
                "Permintaan ditolak: terdeteksi upaya mengubah instruksi sistem (prompt injection)."
            )

    for word in MODIFY_WORDS:
        if re.search(rf"\b{word}\b", text):
            raise AccessDenied(
                "Permintaan ditolak: sistem ini hanya boleh MEMBACA data (read-only). "
                "Perintah hapus/ubah/tambah data tidak diizinkan."
            )

    if role == "Sales_Staff":
        for word in GL_WORDS:
            if word in text:
                raise AccessDenied(
                    "Akses ditolak: role Sales_Staff tidak boleh mengakses data jurnal keuangan (GL_Journals)."
                )


def clean_sql(sql):
    """Bersihkan jawaban AI, kadang AI membungkus query dengan ```sql ... ```"""
    sql = sql.strip()
    sql = re.sub(r"^```(sql)?", "", sql, flags=re.IGNORECASE).strip()
    sql = re.sub(r"```$", "", sql).strip()
    sql = sql.rstrip(";").strip()
    return sql


def check_sql(sql, role):
    """Cek query buatan AI SEBELUM dijalankan ke database."""
    if not sql:
        raise AccessDenied("Query kosong.")

    upper_sql = sql.upper()

    # 1. hanya boleh SELECT
    if not upper_sql.startswith("SELECT"):
        raise AccessDenied("Query ditolak: hanya query SELECT yang diizinkan (read-only).")

    # 2. tidak boleh ada lebih dari 1 perintah atau komentar SQL
    if ";" in sql or "--" in sql or "/*" in sql:
        raise AccessDenied("Query ditolak: tidak boleh ada beberapa perintah atau komentar SQL.")

    # 3. tidak boleh ada perintah yang mengubah data
    for keyword in FORBIDDEN_SQL:
        if re.search(rf"\b{keyword}\b", upper_sql):
            raise AccessDenied(f"Query ditolak: perintah {keyword} tidak diizinkan (read-only).")

    # 4. tidak boleh akses tabel sistem
    lower_sql = sql.lower()
    for table in SYSTEM_TABLES:
        if table in lower_sql:
            raise AccessDenied("Query ditolak: tidak boleh mengakses tabel sistem.")

    # 5. tabel yang dipakai harus sesuai hak akses role
    allowed = ROLE_TABLES[role]
    for table in ALL_TABLES:
        if table not in allowed and re.search(rf"\b{table}\b", sql, re.IGNORECASE):
            raise AccessDenied(f"Akses ditolak: role {role} tidak boleh mengakses tabel {table}.")

    # nama tabel setelah FROM / JOIN juga harus ada di daftar
    used_tables = re.findall(r"\b(?:FROM|JOIN)\s+([A-Za-z_][\w\.\[\]]*)", sql, re.IGNORECASE)
    allowed_lower = [t.lower() for t in allowed]
    for table in used_tables:
        name = table.replace("[", "").replace("]", "").split(".")[-1].lower()
        if name not in allowed_lower:
            raise AccessDenied(f"Akses ditolak: tabel {table} tidak dikenal atau tidak diizinkan.")
