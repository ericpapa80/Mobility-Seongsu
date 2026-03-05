import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_db_available = False
engine = None
async_session = None

try:
    engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _db_available = True
except Exception:
    logger.warning("DB engine creation failed — running in JSON-only mode")


def is_db_available() -> bool:
    return _db_available


async def get_db() -> AsyncSession:
    if not _db_available or async_session is None:
        raise RuntimeError("Database not available")
    async with async_session() as session:
        yield session
