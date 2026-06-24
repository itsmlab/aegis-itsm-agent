"""
AEGIS SaaS — Centralized Configuration
Uses pydantic-settings to load from .env / environment variables.
All paths, API keys, and service endpoints are defined here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    # -- App metadata ------------------------------------------------
    APP_NAME: str = "AEGIS Integration Module"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = False

    # -- Paths (relative to project root) ----------------------------
    PROJECT_ROOT: Path = Path(__file__).parent.parent.resolve()
    PATTERNS_FILE: Path = PROJECT_ROOT / "AEGIS_PATTERNS.md"
    DATASET_PATH: str = str(PROJECT_ROOT / "tickets_dataset.csv")
    CLASSIFIER_DB_PATH: str = "./tickets_db"

    # -- Embedding model ---------------------------------------------
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CLASSIFIER_CONFIDENCE_THRESHOLD: float = 0.45

    # -- LLM Provider ------------------------------------------------
    # Options: "deepseek", "openai", "ollama"
    LLM_PROVIDER: str = "deepseek"
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    LLM_TEMPERATURE: float = 0.1

    # -- PostgreSQL (multi-tenant operational data) ------------------
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/aegis"

    # -- ChromaDB server ---------------------------------------------
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    # If True, uses ChromaDB HTTP client; if False, uses local PersistentClient
    CHROMA_USE_SERVER: bool = False

    # -- Multi-tenancy -----------------------------------------------
    DEFAULT_TENANT_ID: str = "default"
    # If True, all endpoints require X-API-Key authentication
    AUTH_REQUIRED: bool = False
    # Master admin key for bootstrapping (create first admin tenant).
    # If set, this key can access admin endpoints without a DB record.
    ADMIN_API_KEY: Optional[str] = None

    # -- Rate limiting / billing -------------------------------------
    SHIELD_MAX_INCIDENTS_PER_MONTH: int = 50
    GUARD_MAX_INCIDENTS_PER_MONTH: int = 999999  # effectively unlimited

    # -- Server ------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Singleton instance -- import this everywhere
settings = Settings()
