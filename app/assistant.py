import logging

from app import database, formatter, llm, security

log = logging.getLogger("assistant")


def answer_question(question, role):
    """
    Alur utama Text-to-SQL:
    1. cek role
    2. cek pertanyaan (prompt injection, perintah ubah data, hak akses)
    3. AI membuat query SQL
    4. cek query (harus SELECT, tabel sesuai role)
    5. jalankan query ke database (koneksi read-only)
    6. format angka ke Rupiah
    7. AI membuat kalimat jawaban
    """
    security.check_role(role)
    security.check_question(question, role)

    allowed_tables = security.ROLE_TABLES[role]
    sql = llm.generate_sql(question, allowed_tables)
    sql = security.clean_sql(sql)
    log.info("role=%s | pertanyaan=%s | sql=%s", role, question, sql)

    if "TIDAK_BISA" in sql.upper():
        raise security.AccessDenied(
            "Permintaan ditolak: pertanyaan ini di luar hak akses role Anda atau meminta perubahan data."
        )

    security.check_sql(sql, role)

    columns, rows = database.run_query(sql)
    data = formatter.format_rows(columns, rows)

    try:
        answer = llm.generate_answer(question, data)
    except Exception as e:
        # kalau AI gagal membuat kalimat, data tetap dikirim
        log.warning("gagal membuat jawaban: %s", e)
        answer = f"Ditemukan {len(data)} baris data."

    return {
        "status": "ok",
        "role": role,
        "question": question,
        "answer": answer,
        "sql": sql,
        "total_rows": len(data),
        "data": data,
    }
