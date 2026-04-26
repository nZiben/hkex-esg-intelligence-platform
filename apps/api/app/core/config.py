from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]
ROOT_ENV_FILE = REPO_ROOT / ".env"
DEFAULT_SQLITE_URL = f"sqlite:///{(REPO_ROOT / 'esg_chatbot.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", str(ROOT_ENV_FILE)),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Project 7 ESG Chatbot API"
    app_version: str = "0.1.0"

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    database_url: str = Field(
        default=DEFAULT_SQLITE_URL,
        alias="DATABASE_URL",
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://rtekkxiz.bja.sealos.run/v1",
        alias="OPENAI_BASE_URL",
    )
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")

    max_context_chunks: int = Field(default=8, alias="MAX_CONTEXT_CHUNKS")
    chunk_size: int = Field(default=900, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=120, alias="CHUNK_OVERLAP")

    prediction_model_root: str = Field(
        default=str(REPO_ROOT / "models"),
        alias="PREDICTION_MODEL_ROOT",
    )
    prediction_model_version: str = Field(default="hkqaa-deep-regressor-v1", alias="PREDICTION_MODEL_VERSION")
    prediction_max_chunks: int = Field(default=400, alias="PREDICTION_MAX_CHUNKS")
    prediction_batch_size: int = Field(default=64, alias="PREDICTION_BATCH_SIZE")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
