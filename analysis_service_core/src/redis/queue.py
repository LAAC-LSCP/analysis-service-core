import json
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Type

import redis

from analysis_service_core.src.redis import commands
from analysis_service_core.src.redis.commands import Command
from analysis_service_core.src.redis.core_types import RedisInfo


class QueueName(StrEnum):
    COMPLETE_TASK = "complete_task"
    RUN_VTC = "run_vtc"
    RUN_VTC_2 = "run_vtc_2"
    RUN_ALICE = "run_alice"
    RUN_W2V2 = "run_w2v2"
    RUN_ACOUSTICS = "run_acoustics"


@dataclass(frozen=True)
class QueueDict:
    name: QueueName
    command: Type[commands.Command]


class Queue:
    """
    Simple queue adapter class for Redis
    """

    _r: redis.Redis
    _name: QueueName

    def __init__(self, name: QueueName):
        self._name = name
        self._r = redis.Redis(**self._get_redis_host_and_port())

    def _get_redis_host_and_port(self) -> RedisInfo:
        redis_host: str | None = os.environ.get("REDIS_HOST", None)
        redis_port: int = int(os.environ.get("REDIS_PORT", 0))

        if redis_host is None:
            print("'REDIS_HOST' env variable is not set, using 'localhost'")
            redis_host = "localhost"

        if redis_port == 0:
            print("'REDIS_PORT' env variable is not set, using '6379'")
            redis_port = 6379

        return {
            "host": redis_host,
            "port": redis_port,
        }

    def enqueue(self, cmd: Command) -> None:
        self._r.lpush(self._name, json.dumps(cmd.to_dict()))

    def dequeue(self) -> Optional[dict]:
        item = self._r.rpop(self._name)

        if item is not None:
            return json.loads(item)  # type: ignore
        return None
