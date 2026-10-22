import os

from dotenv import load_dotenv

# baca isi file .env (kalau ada)
load_dotenv()

# Setting AI / LLM
# Bisa pakai OpenAI, Groq, Gemini, dll. selama API-nya kompatibel dengan OpenAI
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or None  # kosong = pakai server OpenAI
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_FALLBACK_MODELS = [m.strip() for m in os.getenv("LLM_FALLBACK_MODELS", "").split(",") if m.strip()]

# Setting database
# sqlite = langsung jalan tanpa install apa-apa (untuk testing lokal)
# mssql  = konek ke SQL Server beneran
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
SQLITE_PATH = os.getenv("SQLITE_PATH", "southcity.db")
MSSQL_CONN_STR = os.getenv("MSSQL_CONN_STR", "")
