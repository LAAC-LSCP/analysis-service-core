import json
import os
from enum import StrEnum
from typing import Optional

import redis

from analysis_service_core.src import errors
from analysis_service_core.src.logger import LoggerFactory
from analysis_service_core.src.redis.commands import Command
from analysis_service_core.src.redis.core_types import RedisInfo

logger = LoggerFactory.get_logger(__name__)


class QueueName(StrEnum):
    """
    Encapsulates the different queues available
    throughout the system
    """

    COMPLETE_TASK = "complete_task"
    RUN_VTC = "run_vtc"
    RUN_VTC_2 = "run_vtc_2"
    RUN_ALICE = "run_alice"
    RUN_W2V2 = "run_w2v2"
    RUN_ACOUSTICS = "run_acoustics"
    PROGRESS = "progress"


class Queue:
    """
    The `Queue` class implements a queuing system

    In this case it acts as an adapter for Redis calls

    It lets you push and pull to the specified queue
    """

    _r: redis.Redis
    _name: QueueName

    def __init__(self, name: QueueName):
        """
        Initializes a `Queue` object

        Args:
            name (QueueName): name of the queue
        """
        self._name = name
        try:
            self._r = redis.Redis(**self._get_redis_host_and_port())
        except Exception as e:
            raise errors.RedisConnectionFailed() from e

    def _get_redis_host_and_port(self) -> RedisInfo:
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

    def enqueue(self, cmd: Command) -> None:
        try:
            self._r.lpush(self._name, json.dumps(cmd.to_dict()))
        except Exception as e:
            logger.exception(f"Failed to enqueue cmd {str(cmd)} {self._name}")
            raise errors.QueuePushFailed(str(self._name)) from e

    def dequeue(self) -> Optional[dict]:
        try:
            item = self._r.rpop(self._name)
        except Exception as e:
            logger.exception(f"Couldn't pop from queue {self._name}")
            raise errors.QueuePopFailed(str(self._name)) from e

        if item is not None:
            return json.loads(item)  # type: ignore
        return None
