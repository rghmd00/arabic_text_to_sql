from typing import List, Dict, Any
from decimal import Decimal
from sqlalchemy import text
from langchain_ollama import ChatOllama


def chat_once(prompt: str, client: ChatOllama) -> str:
    try:
        resp = client.invoke(prompt) 
        content = getattr(resp, "content", "")
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        return content or ""
    except Exception as e:
        print("Ollama call failed:", e)
        return ""

def translate_question(question: str, client: ChatOllama) -> str:
    """Translate Arabic to English only if needed, keep English as-is."""

    # Quick heuristic: Arabic has these common characters
    arabic_chars = any(0x0600 <= ord(c) <= 0x06FF for c in question)

    if not arabic_chars:
        print(f"English question (kept original): '{question}'")
        return question

    print(f" Arabic detected, translating...")
    prompt = f"""Translate ONLY this Arabic question to clear English for SQL querying.


Arabic: {question}


English:"""

    english = chat_once(prompt, client).strip()

    # Retry if bad translation
    if not english or len(english) < 5 or "?" not in english:
        prompt = f"""Translate ONLY: {question}


One English question:"""
        english = chat_once(prompt, client).strip()

    print(f" Translated: '{english}'")
    return english



def extract_oracle_schema(engine, schema="HR") -> str:
    query = f"""
    SELECT
        table_name,
        column_name,
        data_type
    FROM all_tab_columns
    WHERE owner = '{schema}'
    ORDER BY table_name, column_id
    """

    schema_dict = {}

    with engine.connect() as conn:
        rows = conn.exec_driver_sql(query).fetchall()

    for table, column, dtype in rows:
        schema_dict.setdefault(table, []).append(f"{column} {dtype}")

    schema_text = []
    for table, cols in schema_dict.items():
        schema_text.append(
            f"{table} ({', '.join(cols)})"
        )

    return "\n".join(schema_text)

def generate_sql(question: str, schema: str, client: ChatOllama) -> str:
    prompt = f"""
You are an expert Oracle SQL assistant for the HR database.

SCHEMA:
{schema}

IMPORTANT TABLES:
- EMPLOYEES (EMPLOYEE_ID, FIRST_NAME, LAST_NAME, SALARY, DEPARTMENT_ID, JOB_ID, HIRE_DATE)
- DEPARTMENTS (DEPARTMENT_ID, DEPARTMENT_NAME, LOCATION_ID)
- JOBS (JOB_ID, JOB_TITLE, MIN_SALARY, MAX_SALARY)
- LOCATIONS (LOCATION_ID, CITY, COUNTRY_ID)
- COUNTRIES (COUNTRY_ID, COUNTRY_NAME, REGION_ID)
- REGIONS (REGION_ID, REGION_NAME)

RULES:
- Use Oracle SQL syntax only.
- Use table aliases (employees e, departments d, jobs j).
- Always qualify columns with table aliases.
- Use FETCH FIRST N ROWS ONLY instead of LIMIT.
- For year extraction, use EXTRACT(YEAR FROM date_column).
- Use SYSDATE for current date.
- Return ONE valid Oracle SELECT query only.
- NO explanation, NO markdown.
- SELECT queries ONLY (NO INSERT, UPDATE, DELETE, DROP, CREATE, ALTER).
- Table and column names are UPPERCASE.
- DO NOT end the SQL statement with a semicolon (;).


Question:
{question}

SQL:
"""
    sql = chat_once(prompt, client).strip().strip("`")
    return sql

def is_safe_sql(sql: str) -> bool:
    """Block all DML/DDL - allow SELECT only for Oracle."""
    sql_upper = sql.strip().upper()
    
    dangerous = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 
        'TRUNCATE', 'ATTACH', 'DETACH', 'REINDEX', 'ANALYZE',
        'PRAGMA', 'BEGIN', 'COMMIT', 'ROLLBACK', 'SAVEPOINT'
    ]
    
    for keyword in dangerous:
        if sql_upper.startswith(keyword):
            return False
    
    # Must start with SELECT
    return sql_upper.startswith('SELECT')

def ask_db(
    question: str,
    engine,                
    schema: str,
    client                 
) -> tuple[str, str, List[Dict[str, Any]]]:
    
    
    sql = ""
    rows_as_dict: List[Dict[str, Any]] = []
    message = "success"
    error_msg = None

    question = question.strip("“”\"").strip(".")

    for attempt in range(2):
        sql = generate_sql(question, schema, client).rstrip(";")
        print("Raw SQL from model:\n", sql)

        if not is_safe_sql(sql):
            message = "الاستعلام غير آمن ولا يمكن تنفيذه"
            return sql, message, []

        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                columns = result.keys()
                rows_as_dict = [
                    {col: float(val) if isinstance(val, Decimal) else val
                     for col, val in zip(columns, row)}
                    for row in result.fetchall()
                ]

            break  # success

        except Exception as e:
            error_msg = str(e)
            print("Execution failed:\n", error_msg)

            if attempt == 0:
                repair_prompt = f"""
You wrote this SQL:

{sql}

The Oracle database returned this error:
{error_msg}

Rewrite the query to fix the error.
Return ONLY valid Oracle SELECT SQL.
Do NOT use semicolons at the end.
"""
                sql = chat_once(repair_prompt, client).strip().rstrip(";")
            else:
                message = "حدث خطأ أثناء تنفيذ الاستعلام"
                return sql, message, []

    if not rows_as_dict:
        message = "لا توجد بيانات متاحة لهذا الطلب"
        return sql, message, []

    return sql, message, rows_as_dict
