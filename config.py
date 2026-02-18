from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
    
    
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Ollama ────────────────────────────────────────────
    ollama_base_url:      str = "http://localhost:11434"
    qwen_coder_model:     str = "qwen2.5-coder:3b"
    qwen_instruct_model:  str = "qwen2.5:3b-instruct"

    # ── API server ────────────────────────────────────────
    api_host:             str = "127.0.0.1"
    api_port:             int = 8000

    # ── Database / file storage ───────────────────────────
    db_extensions:        set[str] = {'.db', '.sqlite', '.sqlite3'}

    # ── Frontend ──────────────────────────────────────────
    api_base_url:         str = "http://localhost:8000"

    # ── Derived (not overridable via env) ─────────────────

    @property
    def db_upload_url(self) -> str:
        return f"{self.api_base_url}/database/upload"

    @property
    def db_query_url(self) -> str:
        return f"{self.api_base_url}/database/query"

    @property
    def db_delete_url(self) -> str:
        return f"{self.api_base_url}/database"

    @property
    def db_schema_url(self) -> str:
        return f"{self.api_base_url}/database"



# Single shared instance — import this everywhere
settings = Settings()