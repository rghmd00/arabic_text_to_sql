# uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
import os, uuid, shutil, tempfile
from pathlib import Path
from contextlib import asynccontextmanager
import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, Form, File
from src.clients import build_client, build_translate_client
from src.UnifiedDatabaseLoader import query_data_base_file, UnifiedDatabaseLoader
from config import settings
from fastapi.middleware.cors import CORSMiddleware


translate_client = build_translate_client()
sql_client       = build_client()
databases        = {}  # file_id -> {filename, path}

     

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for fid in list(databases):
        try:
            os.remove(databases.pop(fid)["path"])
        except Exception:
            pass

app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:8501"] to be more specific
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/database/upload")
async def upload_database(file: UploadFile = File(...)):
    if not file.filename or Path(file.filename).suffix.lower() not in settings.db_extensions:
        raise HTTPException(400, "Only .db, .sqlite, .sqlite3 files are supported")

    fid = uuid.uuid4().hex[:8]
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
        shutil.copyfileobj(file.file, tmp)
        databases[fid] = {"filename": file.filename, "path": tmp.name}

    return {"status": "success", "file_id": fid, "filename": file.filename}


@app.post("/database/query")
async def query_database(file_id: str = Form(...), question: str = Form(...)):
    db = _get_db(file_id)
    result_df, sql = query_data_base_file(db["path"], question, translate_client, sql_client)
    result = result_df.replace({np.nan: None}).astype(object).to_dict("records") if hasattr(result_df, "to_dict") else result_df
    return {"status": "success", "file_id": file_id, "filename": db["filename"], "question": question, "sql": sql, "answer": result}


@app.delete("/database/{file_id}")
async def delete_database(file_id: str):
    if file_id in databases:
        try:
            os.remove(databases.pop(file_id)["path"])
        except Exception:
            pass
    return {"status": "success"}


@app.get("/database/{file_id}/schema")
async def get_schema(file_id: str):
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










