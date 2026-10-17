
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.redis import check_redis_connection, close_redis
from app.services.scheduler import scheduler, register_jobs

configure_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting")

    register_jobs()
    scheduler.start()
    logger.info("Attendance notification scheduler started")

    if check_redis_connection():
        logger.info("Redis connected")
    else:
        logger.warning("Redis is unavailable; report caching is disabled")

    try:
        yield
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("Attendance notification scheduler stopped")

        close_redis()
        logger.info("Application shutting down")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(api_router)

@app.get("/health")
def health_check():
    redis_ok = check_redis_connection()
    return {
        "status": "healthy",
        "application": settings.app_name,
        "version": settings.app_version,
        "redis": "connected" if redis_ok else "unavailable",
    }
