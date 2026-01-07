import json
import os
from typing import Iterable, List

import redis
from redis.client import PubSub as RPubSub

from analysis_service_core.src.redis.channels import ChannelName
from analysis_service_core.src.redis.commands import Command
from analysis_service_core.src.redis.core_types import RedisInfo


class PubSub:
    """
    Simple publish-subscribe wrapper around Redis
    """

    _r: redis.Redis
    _pubsub: RPubSub

    def __init__(self, subscribe_to: List[ChannelName] = []):
        self._r = redis.Redis(**self._get_redis_host_and_port())

        self._pubsub = self._r.pubsub(ignore_subscribe_messages=True)

        self._pubsub.subscribe([channel_name.value for channel_name in subscribe_to])

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

    def publish(self, channel: ChannelName, cmd: Command) -> None:
        self._r.publish(
            channel,
            json.dumps(cmd.to_dict()),
        )

    def listen(self) -> Iterable[dict]:
        return self._pubsub.listen()

    def get_data_from_message(self, message: dict) -> dict:
        return json.loads(message["data"].decode("utf-8"))
