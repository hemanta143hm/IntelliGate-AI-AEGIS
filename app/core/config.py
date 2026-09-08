"""Environment-backed application settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings with project-relative defaults."""

    app_name: str = "IntelliGate AI - AEGIS"
    environment: str = "development"
    database_path: Path = PROJECT_ROOT / "data" / "aegis.sqlite3"
    storage_path: Path = PROJECT_ROOT / "data"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
