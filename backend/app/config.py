from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mobility_seongsu"
    CORS_ORIGINS: str = "http://localhost:5173"
    PORT: int = 8000
    SEOUL_OPEN_DATA_KEY: str = ""

    model_config = {"env_file": "../.env", "extra": "ignore"}

    def model_post_init(self, __context: object) -> None:
        # Railway는 postgresql:// 형식으로 제공 → asyncpg 드라이버용으로 자동 변환
        if self.DATABASE_URL.startswith("postgresql://"):
            object.__setattr__(
                self,
                "DATABASE_URL",
                self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1),
            )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
