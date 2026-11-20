from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Ollama
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "gemma4:12b"
    EMBED_MODEL: str = "nomic-embed-text"

    # Retrieval
    RERANKER_ENABLED: bool = False
    VECTOR_TOP_K: int = 20
    BM25_TOP_K: int = 20
    FINAL_TOP_K: int = 6
    RELEVANCE_THRESHOLD: float = 0.3

    # Ingestion
    MAX_UPLOAD_MB: int = 200
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 100

    # Auth
    PIN_ENABLED: bool = False
    PIN_CODE: str = "1234"

    # Network
    LAN_BIND: bool = False

    # Hardware
    HARDWARE_PROFILE: Literal["STANDARD", "HIGH", "LOW"] = "STANDARD"

    # Paths
    DATA_DIR: str = "./data"
    LOG_FILE: str = "./data/logs/seabot.log"

    @property
    def data_path(self) -> Path:
        p = Path(self.DATA_DIR)
        if not p.is_absolute():
            return (Path(__file__).resolve().parent.parent / p).resolve()
        return p.resolve()

    # Derived helpers (not env vars)
    @property
    def db_url(self) -> str:
        clean_path = str(self.data_path / "seabot.db").replace("\\", "/")
        return f"sqlite+aiosqlite:///{clean_path}"

    @property
    def chroma_path(self) -> str:
        return str(self.data_path / "chroma")

    @property
    def uploads_path(self) -> str:
        return str(self.data_path / "uploads")

    @property
    def thumbnails_path(self) -> str:
        return str(self.data_path / "thumbnails")

    @property
    def fts_db_path(self) -> str:
        return str(self.data_path / "fts.db")

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
