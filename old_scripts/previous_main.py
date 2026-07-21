# # uv run uvicorn main_upload:app --host 127.0.0.1 --port 8000 --reload

# import os
# import shutil
# import uuid
# from pathlib import Path

# from fastapi import FastAPI, HTTPException, UploadFile, File, Form
# from src.database import extract_uploaded_db_schema, query_any_db
# from src.clients import build_client, build_translate_client


# # =====================================================
# # FASTAPI APP
# # =====================================================
# app = FastAPI(title="Database Query API")


# # =====================================================
# # LLM CLIENTS (SAFE TO INIT ON STARTUP)
# # =====================================================
# sql_client = build_client()
# translator_client = build_translate_client()


# async def save_file(file: UploadFile, file_num: str):
#     base_dir = Path(__file__).resolve().parent 
#     print(base_dir)
#     files_dir = base_dir / "data" / "files"
#     print(files_dir)
#     files_dir.mkdir(parents=True, exist_ok=True)

#     filename = file.filename or "document"
#     suffix = Path(filename).suffix
#     file_path = files_dir / f"{file_num}_{filename}"

#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     return file_path, suffix
# # =====================================================
# # MAIN ENDPOINT
# # =====================================================
# @app.post("/query/{file_num}")
# async def process_query(
#     file_num: str,
#     question: str = Form(...),
#     file: UploadFile = File(...)
# ):
#     """
#     Accepts:
#     - question (form field)
#     - SQLite database file (multipart upload)
#     """

#     # sanity check
#     if sql_client is None or translator_client is None:
#         raise HTTPException(
#             status_code=503,
#             detail="Service not ready: LLM clients not initialized"
#         )

#     # save uploaded DB
#     file_path, suffix = await save_file(file,file_num)

#     try:
#         # extract schema from THIS uploaded DB
#         schema = extract_uploaded_db_schema(str(file_path))

#         if not schema:
#             raise ValueError("Failed to extract database schema")

#         df = query_any_db(
#             db_path=str(file_path),
#             question=question,
#             translate_client=translator_client,
#             sql_client=sql_client
#         )

#         return {
#             "results": df.to_dict(orient="records")
#         }

#     except Exception as e:
#         print(f"Error processing query: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Internal Server Error: {str(e)}"
#         )