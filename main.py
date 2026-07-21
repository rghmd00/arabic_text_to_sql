# uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
import os, uuid, tempfile
from pathlib import Path
from contextlib import asynccontextmanager
import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, Form, File, Request
from fastapi.responses import JSONResponse
from src.clients import build_client
from src.UnifiedDatabaseLoader import query_data_base_file, UnifiedDatabaseLoader
from config import settings
from fastapi.middleware.cors import CORSMiddleware


translate_client = build_client(settings.qwen_instruct_model)
sql_client = build_client(settings.qwen_coder_model)
databases = {}  # file_id -> {filename, path}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for fid in list(databases):
        try:
            os.remove(databases.pop(fid)["path"])
        except Exception:
            pass

app = FastAPI(lifespan=lifespan)


# NOTE: wildcard origin + allow_credentials=True is invalid per the CORS
# spec (browsers will reject/ignore the credentialed wildcard combo).
# Pick one: lock down allow_origins to your real frontend origin(s) if you
# need credentials, or drop allow_credentials if "*" is required.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # set to your actual frontend origin(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Guardrail violations (and any other ValueError raised deeper in the
# pipeline, e.g. generate_sql) now surface as a clean 400 instead of an
# unhandled 500.
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


MAX_UPLOAD_BYTES = getattr(settings, "max_upload_bytes", 200 * 1024 * 1024)  # default 200MB


@app.post("/database/upload")
def upload_database(file: UploadFile = File(...)):
    if not file.filename or Path(file.filename).suffix.lower() not in settings.db_extensions:
        raise HTTPException(400, "Only .db, .sqlite, .sqlite3 files are supported")

    fid = uuid.uuid4().hex  
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            tmp_path = tmp.name
            size = 0
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(400, "File too large")
                tmp.write(chunk)
    except HTTPException:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise HTTPException(500, "Failed to save uploaded file")

    databases[fid] = {"filename": file.filename, "path": tmp_path}
    return {"status": "success", "file_id": fid, "filename": file.filename}


@app.post("/database/query")
def query_database(file_id: str = Form(...), question: str = Form(...)):
    db = _get_db(file_id)
    result_df, sql = query_data_base_file(db["path"], question, translate_client, sql_client)
    result = result_df.replace({np.nan: None}).astype(object).to_dict("records") if hasattr(result_df, "to_dict") else result_df
    return {"status": "success", "file_id": file_id, "filename": db["filename"], "question": question, "sql": sql, "answer": result}


@app.delete("/database/{file_id}")
def delete_database(file_id: str):
    if file_id in databases:
        try:
            os.remove(databases.pop(file_id)["path"])
        except Exception:
            pass
    return {"status": "success"}


@app.get("/database/{file_id}/schema")
def get_schema(file_id: str):
    db = _get_db(file_id)
    loader = UnifiedDatabaseLoader(db["path"])
    schema = loader.get_schema()
    loader.close()
    return {"status": "success", "file_id": file_id, "filename": db["filename"], "schema": schema}


@app.get("/health")
async def health():
    return {"status": "healthy"}


def _get_db(file_id: str) -> dict:
    if file_id not in databases or not Path(databases[file_id]["path"]).exists():
        raise HTTPException(404, "Database not found")
    return databases[file_id]


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.api_host, port=settings.api_port, reload=True)