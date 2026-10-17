import logging

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client: Redis | None = None


def get_redis() -> Redis:
    """Return a shared Redis client, creating it on first use."""
    global redis_client

    if redis_client is None:
        password = None
        if settings.redis_password is not None:
            password = settings.redis_password.get_secret_value() or None

        redis_client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=password,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )

    return redis_client


def close_redis() -> None:
    """Close the shared Redis client if it was created."""
    global redis_client

    if redis_client is not None:
        redis_client.close()
        redis_client = None


def check_redis_connection() -> bool:
    """Return True when Redis accepts a PING."""
    try:
        return bool(get_redis().ping())
    except RedisError:
        logger.warning("Redis is unavailable", exc_info=True)
        return False
