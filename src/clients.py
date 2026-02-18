import os
import re 
from langchain_ollama import ChatOllama
from config import settings


# Inside Docker, this will be http://host.docker.internal:11434
# Locally, this will default to http://localhost:11434


OLLAMA_BASE_URL    = settings.ollama_base_url
QWEN_CODER_MODEL   = settings.qwen_coder_model
QWEN_ISTRUCT_MODEL = settings.qwen_instruct_model




def build_client() -> ChatOllama:
    return ChatOllama(
        model= QWEN_CODER_MODEL, 
        temperature=0,
        base_url=OLLAMA_BASE_URL
    )

def build_translate_client() -> ChatOllama:

    return ChatOllama(
        model= QWEN_ISTRUCT_MODEL, 
        temperature=0,
        base_url=OLLAMA_BASE_URL
    )



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
    """
    Use the LLM to translate any non-English question into clear English
    suitable for SQL querying. If the question is already English, keep it as-is.
    """

    prompt = f"""
You are a language detection and translation assistant.

Task:
- If the question is already in English, return it unchanged.
- If the question is NOT in English, translate it into clear, natural English.
- The final output MUST be a single English question suitable for SQL querying.
- Do NOT explain what you did.
- Do NOT add extra text.

Question:
{question}

English question:
"""

    english = chat_once(prompt, client).strip()
    if not english or len(english) < 5:
        print("LLM returned weak output, retrying...")
        english = chat_once(prompt, client).strip()

    print(f"Final English question: '{english}'")
    return english







def generate_sql(question: str, schema: str, client: ChatOllama) -> str:
    """Generate SQL for SQLite database using DuckDB syntax"""
    
    table_names = re.findall(r'^(\w+) \(', schema, re.MULTILINE)
    
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
    
    # Clean response
    sql = re.sub(r'^```sql\s*|\s*```$|^sql\s*', '', sql, flags=re.IGNORECASE).strip(';').strip()
    
    # Fix missing db. prefixes
    for table in table_names:
        sql = re.sub(rf'\b(FROM|JOIN)\s+({table})\b', rf'\1 db.\2', sql, flags=re.IGNORECASE)
    
    return sql







