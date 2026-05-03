"""A collection of classes related to Redis queues."""

import json
from enum import StrEnum
from typing import Optional

import redis

from analysis_service_core.src import errors
from analysis_service_core.src.logger import LoggerFactory
from analysis_service_core.src.redis.commands import Command
from analysis_service_core.src.redis.shared import get_redis_host_and_port

logger = LoggerFactory.get_logger(__name__)


class QueueName(StrEnum):
    """Encapsulates the different queues available throughout the system."""

    COMPLETE_TASK = "complete_task"
    RUN_VTC = "run_vtc"
    RUN_VTC_2 = "run_vtc_2"
    RUN_ALICE = "run_alice"
    RUN_W2V2 = "run_w2v2"
    RUN_ACOUSTICS = "run_acoustics"
    PROGRESS = "progress"


class Queue:
    """The `Queue` class wraps a Redis queue."""

    _r: redis.Redis
    _name: QueueName

    def __init__(self, name: QueueName):
        """Initializes a `Queue` object.

        Args:
            name (QueueName): name of the queue
        """
        self._name = name
        try:
            self._r = redis.Redis(**get_redis_host_and_port())
        except Exception as e:
            raise errors.RedisConnectionFailed() from e

    def enqueue(self, cmd: Command) -> None:
        """Add an item to this queue."""
        try:
            self._r.lpush(self._name, json.dumps(cmd.to_dict()))
        except Exception as e:
            logger.exception(f"Failed to enqueue cmd {str(cmd)} {self._name}")
            raise errors.QueuePushFailed(str(self._name)) from e

    def dequeue(self) -> Optional[dict]:
        """Grab an item from this queue."""
        try:
            item = self._r.rpop(self._name)
        except Exception as e:
            logger.exception(f"Couldn't pop from queue {self._name}")
            raise errors.QueuePopFailed(str(self._name)) from e

        if item is not None:
            return json.loads(item)  # type: ignore
        return None
