import re 
from langchain_ollama import ChatOllama
from config import settings
from src.sql_validate import validate_sql


# Constants
OLLAMA_BASE_URL = settings.ollama_base_url
QWEN_CODER_MODEL = settings.qwen_coder_model
QWEN_INSTRUCT_MODEL = settings.qwen_instruct_model



def build_client(model: str | None) -> ChatOllama:
    """Build ChatOllama client with specified model"""
    model = model or QWEN_CODER_MODEL
    return ChatOllama(
        model=model, 
        temperature=0,
        base_url=OLLAMA_BASE_URL
    )


def chat_once(prompt: str, client: ChatOllama) -> str:
    """Send single prompt to LLM and return response text."""
    try:
        content = client.invoke(prompt).content
        if isinstance(content, str):
            return content
        # Handle multimodal/chunked list responses gracefully
        return "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    except Exception as e:
        print(f"Ollama call failed: {e}")
        raise



def translate_question(question: str, client: ChatOllama) -> str:
    """Translate non-English questions to English for SQL querying"""
    prompt = f"""You are a SQL-focused translation assistant.

Task:
1. If the input is not in English, translate it to natural English.
2. If the input is already in English, refine the grammar and terminology to ensure it is clear for a SQL query (e.g., pluralize nouns, use standard terms like "top" or "highest").
3. Output ONLY the final English question. No explanations.

Question:
{question}

English question:
"""

    english = chat_once(prompt, client).strip()
    print(f"Translated question: '{english}'")
    return english




def generate_sql(question: str, schema: str, client: ChatOllama) -> str:
    """Generate SQL for SQLite database using DuckDB syntax"""
    
    # Extract table names from schema
    table_names = re.findall(r'^(\w+) \(', schema, re.MULTILINE)
    if not table_names:
        raise ValueError("No tables found in schema")
    
    prompt = f"""You are a SQL expert using DuckDB syntax for SQLite databases.

SCHEMA:
{schema}

RULES:
1. Database is attached as 'db'
2. Prefix all tables with 'db.' (e.g., db.Customer, db.Invoice)
3. Use exact table names from schema (case-sensitive)
4. Return ONLY the SQL query - no markdown, no explanation

Question: {question}

SQL:"""
    
    sql = chat_once(prompt, client).strip()
    
    # Clean markdown and extra formatting
    sql = re.sub(r'^```sql\s*|\s*```$|^sql\s*', '', sql, flags=re.IGNORECASE).strip(';').strip()
    
    # Ensure all tables have db. prefix
    for table in table_names:
        sql = re.sub(rf'\b(FROM|JOIN)\s+({table})\b', rf'\1 db.\2', sql, flags=re.IGNORECASE)
    
    
    val_result = validate_sql(sql)
    
    if not val_result.get("is_valid"):
        # Caught by the ValueError handler registered in main.py -> HTTP 400
        raise ValueError(f"Security Guardrail Violation: {val_result.get('error')}")
 
    return sql
