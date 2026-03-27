import os
import warnings

from pydantic_settings import BaseSettings


def _stable_default_secret() -> str:
    """Return a stable default for development. In production, set JWT_SECRET via .env."""
    warnings.warn(
        "JWT_SECRET not set — using an insecure default. "
        "Set JWT_SECRET in .env for production.",
        stacklevel=2,
    )
    return "insecure-dev-secret-change-me"


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/novel.db"
    JWT_SECRET: str = _stable_default_secret()
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours
    ENCRYPTION_KEY: str = ""  # Fernet key for AI API key encryption

    class Config:
        env_file = ".env"


settings = Settings()
