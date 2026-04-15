"""
A general class for pubsubs. These are fairly Redis-native.
In the future you may consider removing this adapter class
in favor of e.g., RabbitMQ queues

Pubsubs in Redis are used when you want instantaneous
communication but also if you don't worry much about loosing data
"""

import json
from enum import StrEnum
from typing import Dict, Iterable, List

import redis
from redis.client import PubSub as RPubSub

from analysis_service_core.src.redis.commands import Command
from analysis_service_core.src.redis.shared import get_redis_host_and_port


class ChannelName(StrEnum):
    """
    Encapsulates different pubsubs
    available
    """

    UPDATE_STATUS = "update_status"


class PubSub:
    """
    The `PubSub` class implements an event bus

    In this case it acts as an adapter for Redis pubsubs

    Consumers can subscribe to pubsubs and/or publish to them
    """

    _r: redis.Redis
    _pubsub: RPubSub

    def __init__(self, subscribe_to: List[ChannelName] = []):
        self._r = redis.Redis(**get_redis_host_and_port())
        self._pubsub = self._r.pubsub(ignore_subscribe_messages=True)
        self._pubsub.subscribe([str(channel_name) for channel_name in subscribe_to])

    def publish(self, channel_name: ChannelName, cmd: Command) -> None:
        self._r.publish(
            channel_name,
            json.dumps(cmd.to_dict()),
        )

    def listen(self) -> Iterable[Dict]:
        return self._pubsub.listen()

    def get_message(self, timeout: float = 0.0) -> Dict:
        return self._pubsub.get_message(timeout=timeout, ignore_subscribe_messages=True)

    def get_data_from_message(self, message: Dict) -> Dict:
        return json.loads(message["data"].decode("utf-8"))

    def get_channel_from_message(self, message: Dict) -> ChannelName:
        return ChannelName(message["channel"].decode("utf-8"))
