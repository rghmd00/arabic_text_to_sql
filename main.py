# uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
import os

from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy import create_engine
from src.database import ask_db,extract_oracle_schema,translate_question
from src.clients import build_client,build_translate_client
from fastapi import FastAPI, HTTPException

   

# ====== FASTAPI APP ======
app = FastAPI(title="Database Query API")


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DATABASE_URL = f"oracle+oracledb://hr:hr@{DB_HOST}:1521/?service_name=XEPDB1"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


schema = extract_oracle_schema(engine=engine, schema="HR")
client = build_client()
translator_client = build_translate_client()


# Request/Response models
class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sql_query: str
    results: List[Dict[str, Any]]




@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Main endpoint - processes natural language to SQL"""
    
    # check all dependencies
    if engine is None or schema is None or client is None or translator_client is None:
        raise HTTPException(
            status_code=503, 
            detail="Service not ready: Database schema or LLM clients not initialized"
        )
    
    try:
        question_translated = translate_question(request.question, translator_client)
        
        sql, message, rows_as_dict = ask_db(
            question=question_translated, 
            engine=engine, 
            schema=schema, 
            client=client
        )
        
        return QueryResponse(
            answer=message,
            sql_query=sql,
            results=rows_as_dict
        )
        
    except Exception as e:
        # Log the error for debugging in Docker logs
        print(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")





@app.get("/")
async def root():
    return {
        "message": "Database Query API",
        "endpoints": {
            "POST /query": "Submit a natural language query"        
        }
    }










# اعرض اسم القسم ومتوسط الرواتب فيه، لكن بس للأقسام اللي متوسط الرواتب أعلى من متوسط رواتب الشركة كلها
# مين الموظفين اللي اشتغلوا في نفس الوظيفة لمدة أطول من متوسط مدة الوظيفة لكل الموظفين؟
# اعرض الموظفين اللي تم تعيينهم قبل مديرهم
# اعرض الأقسام اللي ما فيهاش أي موظف راتبه أعلى من متوسط راتب الشركة
# اعرض متوسط المرتبات لكل Department، ورتّبهم من الأعلى للأقل.
#مين الموظفين اللي مرتباتهم أعلى من متوسط المرتبات في القسم بتاعهم؟












