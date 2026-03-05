import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_db_available = False
engine = None
async_session = None

try:
    _db_url = settings.DATABASE_URL
    # 2차 안전망: config.py validator가 놓친 경우를 대비
    if _db_url.startswith("postgresql://"):
        _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    logger.info("Connecting to DB: %s", _db_url[:40])
    engine = create_async_engine(_db_url, echo=False, future=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _db_available = True
except Exception as e:
    logger.warning("DB engine creation failed — running in JSON-only mode: %s", e)


def is_db_available() -> bool:
    return _db_available


async def get_db() -> AsyncSession:
    if not _db_available or async_session is None:
        raise RuntimeError("Database not available")
    async with async_session() as session:
        yield session
