import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/novel.db"
    JWT_SECRET: str = os.urandom(32).hex()
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours
    ENCRYPTION_KEY: str = ""  # Fernet key for AI API key encryption

    class Config:
        env_file = ".env"


settings = Settings()
