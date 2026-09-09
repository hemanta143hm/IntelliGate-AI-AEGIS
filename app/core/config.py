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
    vision_model: str = "yolo11n.pt"
    vision_confidence: float = 0.35
    vision_interval: int = 1
    vision_frame_size: int = 640
    occupancy_capacity: int | None = None

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
