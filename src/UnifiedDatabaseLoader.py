import duckdb
import pandas as pd
from langchain_ollama import ChatOllama
from src.clients import translate_question, generate_sql


class UnifiedDatabaseLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.conn = duckdb.connect()
        self.conn.execute(f"ATTACH '{file_path}' AS db (TYPE SQLITE)")
    
    def get_schema(self) -> str:
        """Get schema information"""
        tables = self.conn.execute("SHOW TABLES FROM db").fetchall()
        schema_parts = []
        
        for (table_name,) in tables:
            cols = self.conn.execute(f"DESCRIBE db.{table_name}").fetchall()
            col_defs = [f"{name} {dtype}" for name, dtype, *_ in cols]
            schema_parts.append(f"{table_name} ({', '.join(col_defs)})")
        
        return "\n".join(schema_parts)
    
    def query(self, sql: str) -> pd.DataFrame:
        """Execute SQL query"""
        return self.conn.execute(sql).df()
    
    def close(self):
        self.conn.close()


def query_data_base_file(
    file_path: str,
    question: str,
    translate_client: ChatOllama,
    sql_client: ChatOllama
) -> tuple[pd.DataFrame, str]:
    """Query database file with natural language"""
    
    loader = UnifiedDatabaseLoader(file_path)
    
    try:
        schema = loader.get_schema()
        print(f"Schema:\n{schema}\n")
        
        english_q = translate_question(question, translate_client)
        print(f"English question: {english_q}\n")
        
        sql = generate_sql(english_q, schema, sql_client)
        print(f"Generated SQL:\n{sql}\n")
        
        result_df = loader.query(sql)
        print(f"Results ({len(result_df)} rows):")
        print(result_df)
        return result_df , sql
        
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame(),""
    finally:
        loader.close()










