import os
import sqlite3
from pathlib import Path

from app import config

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "schema.sql"


def init_db():
    """Untuk SQLite: buat file database dari schema.sql kalau belum ada."""
    if config.DB_TYPE != "sqlite":
        return  # untuk SQL Server, schema.sql dijalankan manual di SSMS

    if os.path.exists(config.SQLITE_PATH):
        return

    script = SCHEMA_FILE.read_text(encoding="utf-8")
    # schema.sql ditulis untuk SQL Server. SQLite tidak kenal
    # "INT FOREIGN KEY REFERENCES", cukup "INT REFERENCES"
    script = script.replace("FOREIGN KEY REFERENCES", "REFERENCES")

    conn = sqlite3.connect(config.SQLITE_PATH)
    conn.executescript(script)
    conn.commit()
    conn.close()
    print(f"Database SQLite dibuat: {config.SQLITE_PATH}")


def get_connection():
    """Buka koneksi database dalam mode READ-ONLY."""
    if config.DB_TYPE == "mssql":
        import pyodbc  # di-import di sini supaya mode sqlite tidak wajib install pyodbc

        # readonly=True -> koneksi minta akses baca saja.
        # Tetap disarankan pakai user DB yang hanya punya role db_datareader.
        return pyodbc.connect(config.MSSQL_CONN_STR, readonly=True)

    # mode=ro artinya SQLite menolak semua perintah tulis (INSERT/UPDATE/DELETE/DROP)
    db_uri = Path(config.SQLITE_PATH).resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(db_uri, uri=True)


def run_query(sql):
    """Jalankan query, kembalikan (nama_kolom, baris_data)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        rows = [list(row) for row in cursor.fetchall()]
        return columns, rows
    finally:
        conn.close()
