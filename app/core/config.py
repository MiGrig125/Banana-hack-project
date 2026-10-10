"""Application configuration loaded from environment variables."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


def _bool(val: Optional[str], default: bool = False) -> bool:
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _int(val: Optional[str], default: int) -> int:
    try:
        return int(val) if val is not None else default
    except ValueError:
        return default


class Settings:
    """Central application settings (env-based)."""

    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "AI Photo Studio")
        self.app_env: str = os.getenv("APP_ENV", "development")
        self.debug: bool = _bool(os.getenv("DEBUG"), True)
        self.host: str = os.getenv("HOST", "0.0.0.0")
        self.port: int = _int(os.getenv("PORT"), 8000)

        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./ai_photo.db")

        self.upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
        self.output_dir: str = os.getenv("OUTPUT_DIR", "outputs")
        self.max_upload_size_mb: int = _int(os.getenv("MAX_UPLOAD_SIZE_MB"), 15)
        self.max_image_dimension: int = _int(os.getenv("MAX_IMAGE_DIMENSION"), 4096)
        self.max_image_count: int = _int(os.getenv("MAX_IMAGE_COUNT"), 4)

        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY") or None
        self.openai_image_model: str = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
        self.openai_vision_model: str = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")

        self.xai_api_key: Optional[str] = os.getenv("XAI_API_KEY") or None
        self.xai_image_model: str = os.getenv("XAI_IMAGE_MODEL", "grok-imagine-image")

        self.default_image_provider: str = os.getenv("DEFAULT_IMAGE_PROVIDER", "openai")
        self.default_vision_provider: str = os.getenv("DEFAULT_VISION_PROVIDER", "openai")

        self.task_timeout_seconds: int = _int(os.getenv("TASK_TIMEOUT_SECONDS"), 180)
        self.enable_rate_limit: bool = _bool(os.getenv("ENABLE_RATE_LIMIT"), False)

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent

    @property
    def upload_path(self) -> Path:
        path = self.base_dir / self.upload_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def output_path(self) -> Path:
        path = self.base_dir / self.output_dir
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
