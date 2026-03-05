from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mobility_seongsu"
    CORS_ORIGINS: str = "http://localhost:5173"
    PORT: int = 8000
    SEOUL_OPEN_DATA_KEY: str = ""

    model_config = {"env_file": "../.env", "extra": "ignore"}

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_db_url(cls, v: str) -> str:
        # Railway는 postgresql:// 형식으로 제공 → asyncpg 드라이버용으로 자동 변환
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()
