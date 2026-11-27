"""Environment configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Defaults keep the local API in empty/demo-safe mode."""

    model_config = SettingsConfigDict(env_prefix="ARM_", env_file=".env", extra="ignore")

    data_dir: Path = Path("data/processed")
    annotation_db: Path = Path("data/annotations.sqlite3")
    duckdb_file: Path = Path("data/analysis.duckdb")
    api_token: str = ""
    allow_unauthenticated_writes: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    page_size_max: int = 100

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
