import time
import openai
from openai import OpenAI

from app import config

# Penjelasan tiap tabel untuk AI.
# Sengaja dipisah per tabel supaya role Sales_Staff tidak pernah "melihat" GL_Journals.
TABLE_INFO = {
    "Units": """Units (
    UnitID INT PRIMARY KEY,
    UnitNumber VARCHAR(20),   -- nomor unit, contoh 'SM 1201'
    Tower VARCHAR(20),        -- 'Summer Tower' / 'Spring Tower'
    Status VARCHAR(20)        -- 'Occupied', 'Vacant', 'Sold'
)""",
    "Sales_Contracts": """Sales_Contracts (
    ContractID INT PRIMARY KEY,
    UnitID INT,               -- relasi ke Units.UnitID
    CustomerName VARCHAR(100),
    SalesAmount DECIMAL(18,2),-- nilai kontrak penjualan
    ContractDate DATE
)""",
    "Invoices_Billing": """Invoices_Billing (
    InvoiceID INT PRIMARY KEY,
    ContractID INT,           -- relasi ke Sales_Contracts.ContractID
    PeriodMonth INT,          -- bulan tagihan (1-12)
    PeriodYear INT,
    AmountBilled DECIMAL(18,2),
    AmountPaid DECIMAL(18,2), -- sisa tunggakan = AmountBilled - AmountPaid
    DueDate DATE
)""",
    "GL_Journals": """GL_Journals (
    JournalID INT PRIMARY KEY,
    AccountCode VARCHAR(20),
    AccountName VARCHAR(100), -- contoh 'Kas & Bank', 'Pendapatan Sales Unit'
    Debit DECIMAL(18,2),
    Credit DECIMAL(18,2),
    TransactionDate DATE
)""",
}

SQL_PROMPT = """Kamu adalah asisten yang mengubah pertanyaan menjadi query SQL
untuk database ERP properti SouthCity.

Tabel yang BOLEH kamu pakai:
{schema}

Aturan:
1. Buat tepat SATU query SELECT. Jangan pernah membuat DELETE, UPDATE, INSERT, DROP, ALTER, atau perintah lain yang mengubah data.
2. Kalau pertanyaan meminta mengubah/menghapus data, atau membutuhkan tabel yang tidak ada di daftar di atas, jawab persis dengan kata: TIDAK_BISA
3. Gunakan dialek {dialect}.
4. Cari nama customer pakai LIKE, contoh: CustomerName LIKE '%Budi Santoso%'
5. Filter tanggal pakai rentang, contoh: TransactionDate >= '2026-01-01' AND TransactionDate < '2026-02-01'
6. Kalau pertanyaan tentang unit tertentu, mulai dari tabel Units lalu LEFT JOIN ke tabel lain, supaya unit tetap tampil walaupun belum ada transaksi.
7. Kalau ditanya "berapa total/sisa", pakai SUM dan beri alias yang jelas, contoh: TotalTunggakan, TotalNilaiKontrak.
8. Jangan pakai komentar SQL dan jangan pakai titik koma.
9. Balas HANYA dengan query SQL-nya saja, tanpa penjelasan.
"""

ANSWER_PROMPT = """Pertanyaan dari manajemen:
{question}

Hasil query dari database (nilai uang sudah dalam format Rupiah):
{data}

Tulis jawaban singkat (1-3 kalimat) dalam Bahasa Indonesia.
Pakai angka persis seperti di data, jangan mengarang angka sendiri.
Kalau datanya kosong atau bernilai null, jelaskan bahwa datanya tidak ditemukan / belum ada transaksi.
"""


def _get_client():
    return OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL, max_retries=0)


def _ask_llm(prompt_system, prompt_user):
    models = [config.LLM_MODEL]
    for m in getattr(config, "LLM_FALLBACK_MODELS", []):
        if m not in models:
            models.append(m)
    if "gemini" in config.LLM_MODEL:
        for fallback in ["gemini-3.5-flash", "gemini-3.6-flash"]:
            if fallback not in models:
                models.append(fallback)

    last_error = None
    for model_name in models:
        for attempt in range(2):
            try:
                response = _get_client().chat.completions.create(
                    model=model_name,
                    temperature=0,  # 0 supaya jawabannya konsisten
                    messages=[
                        {"role": "system", "content": prompt_system},
                        {"role": "user", "content": prompt_user},
                    ],
                )
                return response.choices[0].message.content.strip()
            except (openai.RateLimitError, openai.InternalServerError) as e:
                last_error = e
                time.sleep(1)
                continue
    if last_error:
        raise last_error


def build_schema(allowed_tables):
    return "\n\n".join(TABLE_INFO[t] for t in allowed_tables)


def generate_sql(question, allowed_tables):
    """Langkah 1: pertanyaan bahasa manusia -> query SQL."""
    dialect = "Microsoft SQL Server (T-SQL)" if config.DB_TYPE == "mssql" else "SQLite"
    system_prompt = SQL_PROMPT.format(schema=build_schema(allowed_tables), dialect=dialect)
    return _ask_llm(system_prompt, question)


def generate_answer(question, data):
    """Langkah 2: hasil query -> kalimat jawaban."""
    if not data:
        data_text = "(tidak ada data)"
    else:
        # cukup kirim 20 baris pertama ke AI, sisanya tetap ada di tabel response
        data_text = "\n".join(str(row) for row in data[:20])

    prompt = ANSWER_PROMPT.format(question=question, data=data_text)
    return _ask_llm("Kamu adalah asisten data untuk manajemen SouthCity.", prompt)
