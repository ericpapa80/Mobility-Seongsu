from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mobility_seongsu"
    CORS_ORIGINS: str = "http://localhost:5173"
    PORT: int = 8000
    SEOUL_OPEN_DATA_KEY: str = ""

    model_config = {"env_file": "../.env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
