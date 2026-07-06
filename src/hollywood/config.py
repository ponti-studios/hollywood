from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class HollywoodSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HOLLYWOOD_",
        extra="ignore",
    )

    data_dir: Path = Path("data")
    db_path: Path = Path("data/hollywood.duckdb")

    @property
    def resolved_data_dir(self) -> Path:
        """Resolve data_dir to an absolute path so Prefect temp CWDs don't break."""
        p = self.data_dir
        if not p.is_absolute():
            # Resolve relative to the project root (where .env lives), not CWD
            p = Path(__file__).resolve().parent.parent.parent / p
        return p

    @property
    def resolved_db_path(self) -> Path:
        p = self.db_path
        if not p.is_absolute():
            p = Path(__file__).resolve().parent.parent.parent / p
        return p
    log_level: str = "INFO"
    concurrency: int = Field(default=4, ge=1, le=16)
    retry_count: int = Field(default=2, ge=0, le=10)
    user_agent: str = "ResearchBot/0.2 contact@example.com"
    request_timeout_seconds: int = Field(default=30, ge=5, le=300)
    tmdb_api_key: str | None = Field(default=None, validation_alias="TMDB_API_KEY")

    @property
    def raw_dir(self) -> Path:
        return self.resolved_data_dir / "raw"

    @property
    def parquet_dir(self) -> Path:
        return self.resolved_data_dir / "parquet"

    def ensure_directories(self) -> None:
        self.resolved_data_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.parquet_dir.mkdir(parents=True, exist_ok=True)
        self.resolved_db_path.parent.mkdir(parents=True, exist_ok=True)
