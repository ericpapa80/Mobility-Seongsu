import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db.database import engine, is_db_available
from app.api import bus, map_data

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if is_db_available() and engine is not None:
        try:
            from app.db.models import Base
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("PostGIS tables created/verified")
        except Exception as e:
            logger.warning("DB init failed, falling back to JSON mode: %s", e)
            app.state._db_init_error = str(e)[:300]
            from app.db import database
            database._db_available = False
    else:
        logger.info("No DATABASE_URL or DB unavailable — running in JSON-only mode")
        app.state._db_init_error = "engine_not_created"
    yield
    if is_db_available() and engine is not None:
        await engine.dispose()


settings = get_settings()

app = FastAPI(
    title="Mobility Seongsu API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bus.router, prefix="/api")
app.include_router(map_data.router, prefix="/api")


@app.get("/api/health")
async def health():
    info = {"status": "ok", "db": is_db_available()}
    if is_db_available() and engine is not None:
        try:
            from sqlalchemy import text
            async with engine.connect() as conn:
                row = await conn.execute(text("SELECT 1"))
                info["db_ping"] = "ok"
        except Exception as e:
            info["db_ping"] = str(e)[:200]
    else:
        info["db_reason"] = getattr(app.state, "_db_init_error", "engine not created or lifespan failed")
    return info


frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
