import logging
from pathlib import Path

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import assistant, config, database
from app.security import AccessDenied

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="SouthCity AI Data Query Assistant",
    description="Tanya data ERP pakai bahasa sehari-hari, AI akan mengubahnya jadi query SQL.",
)

# siapkan database saat aplikasi start
database.init_db()


class QuestionRequest(BaseModel):
    question: str


@app.get("/info")
def info():
    """Dipakai tampilan web untuk menampilkan database & model AI yang aktif."""
    if config.DB_TYPE == "mssql":
        db_name = "SQL Server"
    else:
        db_name = f"{config.SQLITE_PATH} (SQLite)"
    return {"database": db_name, "model": config.LLM_MODEL}


@app.post("/ask")
def ask(
    body: QuestionRequest,
    # convert_underscores=False supaya nama header tetap "user_role" sesuai soal
    user_role: str = Header(..., convert_underscores=False, description="Sales_Staff atau Management"),
):
    try:
        return assistant.answer_question(body.question, user_role)
    except AccessDenied as e:
        return JSONResponse(status_code=403, content={"status": "ditolak", "message": str(e)})
    except Exception as e:
        logging.exception("error saat memproses pertanyaan")
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Terjadi kesalahan: {e}"})


# Tampilan web (folder static/) dibuka di http://127.0.0.1:8000
# Ditaruh paling bawah supaya tidak menutupi route /ask, /info, dan /docs
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
