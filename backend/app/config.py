from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class Settings(BaseSettings):
    app_name: str = "RAG QA System"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    frontend_origin: str = "http://localhost:5173"
    data_dir: str = str(DEFAULT_DATA_DIR)

    deepseek_api_key: str = ""
    openai_api_key: str = ""
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_cache_dir: str = str(DEFAULT_DATA_DIR / "embedding_models")
    embedding_batch_size: int = 20
    embedding_max_retries: int = 3
    chunk_size: int = 500
    chunk_overlap: int = 50
    enable_reranker: bool = False
    reranker_model: str = "BAAI/bge-reranker-base"
    reranker_top_k: int = 5
    reranker_use_fp16: bool = False  # 半精度仅在 GPU 有意义；CPU 必须 False，否则推理报错
    max_history_messages: int = 20  # 多轮对话带入的历史消息上限（约 10 轮）；0 = 关闭多轮

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("api_v1_prefix")
    @classmethod
    def normalize_api_prefix(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("/"):
            value = f"/{value}"
        return value.rstrip("/") or "/api/v1"

    @field_validator("embedding_provider")
    @classmethod
    def normalize_embedding_provider(cls, value: str) -> str:
        provider = value.strip().lower()
        if provider == "local":
            return "fastembed"
        if provider not in {"openai", "fastembed"}:
            raise ValueError("must be one of: openai, fastembed")
        return provider

    @field_validator(
        "embedding_batch_size",
        "embedding_max_retries",
        "chunk_size",
        "reranker_top_k",
    )
    @classmethod
    def require_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be positive")
        return value

    @field_validator("chunk_overlap", "max_history_messages")
    @classmethod
    def require_non_negative_int(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must be non-negative")
        return value


settings = Settings()
