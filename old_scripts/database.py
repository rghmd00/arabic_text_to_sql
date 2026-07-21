# import re

# from typing import List, Dict, Any
# from decimal import Decimal
# from sqlalchemy import text
# from langchain_ollama import ChatOllama
# import duckdb
# import pandas as pd



# def extract_oracle_schema(engine, schema="HR") -> str:
#     query = f"""
#     SELECT
#         table_name,
#         column_name,
#         data_type
#     FROM all_tab_columns
#     WHERE owner = '{schema}'
#     ORDER BY table_name, column_id
#     """

#     schema_dict = {}

#     with engine.connect() as conn:
#         rows = conn.exec_driver_sql(query).fetchall()

#     for table, column, dtype in rows:
#         schema_dict.setdefault(table, []).append(f"{column} {dtype}")

#     schema_text = []
#     for table, cols in schema_dict.items():
#         schema_text.append(
#             f"{table} ({', '.join(cols)})"
#         )

#     return "\n".join(schema_text)

# def generate_sql(question: str, schema: str, client: ChatOllama) -> str:
#     prompt = f"""
# You are an expert Oracle SQL assistant for the HR database.

# SCHEMA:
# {schema}

# IMPORTANT TABLES:
# - EMPLOYEES (EMPLOYEE_ID, FIRST_NAME, LAST_NAME, SALARY, DEPARTMENT_ID, JOB_ID, HIRE_DATE)
# - DEPARTMENTS (DEPARTMENT_ID, DEPARTMENT_NAME, LOCATION_ID)
# - JOBS (JOB_ID, JOB_TITLE, MIN_SALARY, MAX_SALARY)
# - LOCATIONS (LOCATION_ID, CITY, COUNTRY_ID)
# - COUNTRIES (COUNTRY_ID, COUNTRY_NAME, REGION_ID)
# - REGIONS (REGION_ID, REGION_NAME)

# RULES:
# - Use Oracle SQL syntax only.
# - Use table aliases (employees e, departments d, jobs j).
# - Always qualify columns with table aliases.
# - Use FETCH FIRST N ROWS ONLY instead of LIMIT.
# - For year extraction, use EXTRACT(YEAR FROM date_column).
# - Use SYSDATE for current date.
# - Return ONE valid Oracle SELECT query only.
# - NO explanation, NO markdown.
# - SELECT queries ONLY (NO INSERT, UPDATE, DELETE, DROP, CREATE, ALTER).
# - Table and column names are UPPERCASE.
# - DO NOT end the SQL statement with a semicolon (;).


# Question:
# {question}

# SQL:
# """
#     sql = chat_once(prompt, client).strip().strip("`")
#     return sql

# def is_safe_sql(sql: str) -> bool:
#     """Block all DML/DDL - allow SELECT only for Oracle."""
#     sql_upper = sql.strip().upper()
    
#     dangerous = [
#         'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 
#         'TRUNCATE', 'ATTACH', 'DETACH', 'REINDEX', 'ANALYZE',
#         'PRAGMA', 'BEGIN', 'COMMIT', 'ROLLBACK', 'SAVEPOINT'
#     ]
    
#     for keyword in dangerous:
#         if sql_upper.startswith(keyword):
#             return False
    
#     # Must start with SELECT
#     return sql_upper.startswith('SELECT')

# def ask_db(
#     question: str,
#     engine,                
#     schema: str,
#     client                 
# ) -> tuple[str, str, List[Dict[str, Any]]]:
    
    
#     sql = ""
#     rows_as_dict: List[Dict[str, Any]] = []
#     message = "success"
#     error_msg = None

#     question = question.strip("“”\"").strip(".")

#     for attempt in range(2):
#         sql = generate_sql(question, schema, client).rstrip(";")
#         print("Raw SQL from model:\n", sql)

#         if not is_safe_sql(sql):
#             message = "الاستعلام غير آمن ولا يمكن تنفيذه"
#             return sql, message, []

#         try:
#             with engine.connect() as conn:
#                 result = conn.execute(text(sql))
#                 columns = result.keys()
#                 rows_as_dict = [
#                     {col: float(val) if isinstance(val, Decimal) else val
#                      for col, val in zip(columns, row)}
#                     for row in result.fetchall()
#                 ]

#             break  # success

#         except Exception as e:
#             error_msg = str(e)
#             print("Execution failed:\n", error_msg)

#             if attempt == 0:
#                 repair_prompt = f"""
# You wrote this SQL:

# {sql}

# The Oracle database returned this error:
# {error_msg}

# Rewrite the query to fix the error.
# Return ONLY valid Oracle SELECT SQL.
# Do NOT use semicolons at the end.
# """
#                 sql = chat_once(repair_prompt, client).strip().rstrip(";")
#             else:
#                 message = "حدث خطأ أثناء تنفيذ الاستعلام"
#                 return sql, message, []

#     if not rows_as_dict:
#         message = "لا توجد بيانات متاحة لهذا الطلب"
#         return sql, message, []

#     return sql, message, rows_as_dict


# ###############################################################################################################

# # def generate_sql_2(question: str, schema: str, client: ChatOllama) -> str:
# #     """Generate SQL for any SQLite database using DuckDB syntax"""
# #     prompt = f"""
# # You are an expert SQL assistant using DuckDB syntax for SQLite databases.

# # SCHEMA:
# # {schema}

# # The database is attached as 'db'. Reference tables as: db.table_name

# # CRITICAL: ALWAYS use 'db.' prefix before table names!
# # Example: SELECT * FROM db.employees WHERE salary = (SELECT MAX(salary) FROM db.employees)

# # RULES:
# # - Reference tables with 'db.' prefix: SELECT * FROM db.employees
# # - For joins: SELECT * FROM db.employees e JOIN db.departments d ON e.department_id = d.department_id
# # - For subqueries: also use db. prefix in the subquery
# # - Use LIMIT instead of FETCH FIRST for top N results
# # - Return ONE valid SELECT query only
# # - NO explanation, NO markdown, NO semicolons

# # Question:
# # {question}

# # SQL:
# # """
# #     sql = chat_once(prompt, client).strip().strip("`").strip(";")
    
# #     # Post-process: Add db. prefix to all table names
# #     import re
# #     table_names = re.findall(r'^(\w+) \(', schema, re.MULTILINE)
    
# #     for table in table_names:
# #         # Add db. prefix if missing
# #         sql = re.sub(rf'\bFROM\s+{table}\b', f'FROM db.{table}', sql, flags=re.IGNORECASE)
# #         sql = re.sub(rf'\bJOIN\s+{table}\b', f'JOIN db.{table}', sql, flags=re.IGNORECASE)
# #         sql = re.sub(rf'\bINTO\s+{table}\b', f'INTO db.{table}', sql, flags=re.IGNORECASE)
    
# #     return sql



# def extract_uploaded_db_schema(db_path: str) -> str:
#     """Extract schema from any SQLite database using DuckDB"""
#     conn = duckdb.connect()
#     conn.execute(f"ATTACH '{db_path}' AS db (TYPE SQLITE)")
    
#     # Get all tables
#     tables = conn.execute("SHOW TABLES FROM db").fetchall()
    
#     schema_dict = {}
    
#     for (table_name,) in tables:
#         # Get a sample row to infer schema
#         sample = conn.execute(f"SELECT * FROM db.{table_name} LIMIT 0").description
#         schema_dict[table_name] = [f"{col[0]} {col[1]}" for col in sample]
    
#     # Format schema text
#     schema_text = []
#     for table, cols in schema_dict.items():
#         schema_text.append(f"{table} ({', '.join(cols)})")
    
#     conn.close()
#     return "\n".join(schema_text)

# def query_any_db(db_path: str, question: str, translate_client: ChatOllama, sql_client: ChatOllama) -> pd.DataFrame:
#     """Query any SQLite database"""
    
#     print(f"✓ Querying database: {db_path}\n")
    
#     # 1. Extract schema
#     schema = extract_uploaded_db_schema(db_path)
#     print(f"Database Schema:\n{schema}\n")
    
#     # 2. Translate question
#     english_q = translate_question(question, translate_client)
#     print(f"English question: {english_q}\n")
    
#     # 3. Generate SQL
#     sql = generate_sql_2(english_q, schema, sql_client)
#     print(f"Generated SQL:\n{sql}\n")
    
#     # 4. Execute
#     try:
#         conn = duckdb.connect()
#         conn.execute(f"ATTACH '{db_path}' AS db (TYPE SQLITE)")
#         result_df = conn.execute(sql).df()
#         conn.close()
        
#         print(f"Results ({len(result_df)} rows):")
#         print(result_df)
#         return result_df
        
#     except Exception as e:
#         print(f"Error executing SQL: {e}")
#         print(f"Generated SQL was:\n{sql}")
#         return pd.DataFrame()




