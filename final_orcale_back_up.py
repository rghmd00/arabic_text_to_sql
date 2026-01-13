import os 

import streamlit as st
import arabic_reshaper
from bidi.algorithm import get_display
from langchain_ollama import ChatOllama
import pandas as pd
from sqlalchemy import create_engine
from src.sidebar import sidebar_schema
from src.chat_bot_ui import render_hr_database_query
from typing import List, Dict, Any
from decimal import Decimal
from sqlalchemy import text

DB_HOST = os.getenv("DB_HOST", "localhost") 
DATABASE_URL = f"oracle+oracledb://hr:hr@{DB_HOST}:1521/?service_name=XEPDB1"

model = "qwen2.5-coder:3b"
translator_model = "qwen2.5:3b-instruct"



def fix_arabic_for_terminal(text: str) -> str:
    try:
        reshaped = arabic_reshaper.reshape(text)
        return str(get_display(reshaped))
    except Exception as e:
        print(f"[warn] Arabic reshaping failed, using raw text. Error: {e}")
        return text

def build_client() -> ChatOllama:
    return ChatOllama(model="qwen2.5-coder:3b", temperature=0)

def build_translate_client() -> ChatOllama:
    return ChatOllama(model="qwen2.5:3b-instruct", temperature=0)

def chat_once(prompt: str, client: ChatOllama) -> str:
    try:
        resp = client.invoke(prompt)  # resp is an AIMessage
        # LangChain messages always have `.content` as str or list of chunks
        content = getattr(resp, "content", "")
        if isinstance(content, list):
            # join any chunked content
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

    # Arabic detected - translate
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
    
    # Block dangerous keywords
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

    # Clean question
    question = question.strip("“”\"").strip(".")

    for attempt in range(2):
        # 1️⃣ Generate SQL from LLM
        sql = generate_sql(question, schema, client).rstrip(";")
        print("Raw SQL from model:\n", sql)

        # 2️⃣ Safety check
        if not is_safe_sql(sql):
            message = "الاستعلام غير آمن ولا يمكن تنفيذه"
            return sql, message, []

        try:
            # 3️⃣ Execute SQL using SQLAlchemy
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
                # 4️⃣ Attempt repair once using LLM
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

    # 5️⃣ Empty result handling
    if not rows_as_dict:
        message = "لا توجد بيانات متاحة لهذا الطلب"
        return sql, message, []

    # ✅ Return SQL, message (empty string if OK), and rows
    return sql, message, rows_as_dict


##################################################################################################
# Streamlit chatbot UI
##################################################################################################

def rtl(text):
    return f'<div style="direction: rtl; text-align: right;">{text}</div>'

def ltr(text):
    return f'<div style="direction: ltr; text-align: left;">{text}</div>'





@st.cache_resource
def get_engine():
    return create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


def main():
    render_hr_database_query()
    engine = get_engine()
    print(f"Engine ID : {id(engine)}" )

    # Initialize session state
    if "engine" not in st.session_state:
        schema = extract_oracle_schema(engine=engine, schema="HR")
        st.session_state.schema = schema
        st.session_state.client = build_client()
        st.session_state.translator_client = build_translate_client()
        st.session_state.messages = []


    schema = st.session_state.schema
    client = st.session_state.client
    translator_client = st.session_state.translator_client

    
    with st.sidebar:
        sidebar_schema(engine)


    # MAIN CHAT AREA - Full width, perfect display!
    # Render chat history
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        with st.chat_message(role):
            if role == "user":
                st.markdown(rtl(content), unsafe_allow_html=True)
            else:
                # Parse structured assistant responses
                if content.startswith("**Answer:**") or "**الإجابة:**" in content:
                    parts = content.split("\n\n")
                    answer_part = parts[0].replace("**Answer:** ", "").replace("**الإجابة:** ", "")
                    sql_part = parts[1].replace("**SQL:**\n", "").replace("**الاستعلام:**\n", "")
                    raw_part = parts[2].replace("**Results:**\n", "").replace("**النتائج الخام:**\n", "")

                    st.markdown("### الإجابة")
                    st.markdown(ltr(answer_part), unsafe_allow_html=True)
                    st.markdown("---")

                    st.markdown("###  SQL")
                    st.code(
                        sql_part.strip(), 
                        language="sql",
                        line_numbers=True,
                        wrap_lines=True,
                        height=250
                    )
                    st.markdown("---")

                    st.markdown("### النتائج")
                    try:
                        import ast
                        raw_data = ast.literal_eval(raw_part)
                        if isinstance(raw_data, list) and len(raw_data) > 0:
                            df = pd.DataFrame(raw_data)
                            for col in df.select_dtypes(include=['object']):
                                df[col] = df[col].apply(lambda x: str(x) if x is not None else None)
                            st.dataframe(df, width="stretch", hide_index=True)
                        else:
                            st.code(str(raw_data), language="python")
                    except:
                        st.code(raw_part, language="python")
                else:
                    st.markdown(ltr(content), unsafe_allow_html=True)

    # Handle new user input
    user_input = st.chat_input("اكتب سؤالك هنا...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(rtl(user_input), unsafe_allow_html=True)

        # Process assistant response
        with st.chat_message("assistant"):
            try:
                question_translated = translate_question(user_input, translator_client)
                sql_query, message, rows_as_dict = ask_db(question_translated, engine, schema, client)

                # Normalize Oracle types before display
                if isinstance(rows_as_dict, list) and len(rows_as_dict) > 0:
                    df = pd.DataFrame(rows_as_dict)
                    for col in df.select_dtypes(include=['object']):
                        df[col] = df[col].apply(lambda x: str(x) if x is not None else None)
                else:
                    df = None


                # Display SQL - VERTICAL LTR FORMAT
                st.markdown("### SQL")
                st.code(
                    sql_query, 
                    language="sql",
                    line_numbers=True,
                    wrap_lines=True,
                    height=250
                )
                st.markdown("---")
                #######################################################################################
                # Display results
                st.markdown("### النتائج")
                if df is not None:
                    st.dataframe(df, width="stretch", hide_index=True)

                else:
                    st.code(str(rows_as_dict), language="python")
                ############################################################################################

                # Store structured response
                full_response = f"**\n\n**SQL:**\n{sql_query}\n\n**النتائج الخام:**\n{str(rows_as_dict)}"
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                err = f"[error] حدث خطأ غير متوقّع أثناء تشغيل البرنامج: {e}"
                st.markdown(ltr(err), unsafe_allow_html=True)
                st.session_state.messages.append({"role": "assistant", "content": err})



if __name__ == "__main__":
    main()
















# اعرض اسم القسم ومتوسط الرواتب فيه، لكن بس للأقسام اللي متوسط الرواتب أعلى من متوسط رواتب الشركة كلها
# مين الموظفين اللي اشتغلوا في نفس الوظيفة لمدة أطول من متوسط مدة الوظيفة لكل الموظفين؟
# اعرض الموظفين اللي تم تعيينهم قبل مديرهم
# اعرض الأقسام اللي ما فيهاش أي موظف راتبه أعلى من متوسط راتب الشركة
# اعرض متوسط المرتبات لكل Department، ورتّبهم من الأعلى للأقل.
#مين الموظفين اللي مرتباتهم أعلى من متوسط المرتبات في القسم بتاعهم؟









# Langgraph
# csv better results display
# integrate work