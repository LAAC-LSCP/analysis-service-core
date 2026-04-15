import os

from analysis_service_core.src.logger import LoggerFactory
from analysis_service_core.src.redis.core_types import RedisInfo

logger = LoggerFactory.get_logger(__name__)


def get_redis_host_and_port() -> RedisInfo:
    redis_host: str | None = os.environ.get("REDIS_HOST", None)
    redis_port: int = int(os.environ.get("REDIS_PORT", 0))

    if redis_host is None:
        logger.warning("'REDIS_HOST' env variable is not set, using 'localhost'")
        redis_host = "localhost"

    if redis_port == 0:
        logger.warning("'REDIS_PORT' env variable is not set, using '6379'")
        redis_port = 6379

    return {
        "host": redis_host,
        "port": redis_port,
    }
