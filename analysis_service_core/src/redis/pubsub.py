"""A general class for pubsubs.

Note that pubsubs are fairly Redis-native. In the future you may consider removing this
adapter class in favor of e.g., RabbitMQ queues.

Pubsubs in Redis are used when you want instantaneous communication but also if you
don't worry much about loosing data.
"""

import json
from enum import StrEnum
from typing import Dict, Iterable, List, TypeAlias, TypedDict

import redis
from redis.client import PubSub as RPubSub

from analysis_service_core.src.redis.commands import Command
from analysis_service_core.src.redis.shared import get_redis_host_and_port

Data: TypeAlias = Dict


class ChannelName(StrEnum):
    """Enumeration of different available pubsubs."""

    UPDATE_STATUS = "update_status"


class Message(TypedDict):
    """Represents a Redis-py message object."""

    channel: ChannelName
    data: Data


class PubSub:
    """The `PubSub` class adapts the notion of an event bus.

    In this case it acts as an adapter for Redis pubsubs. Consumers can subscribe to
    or publish to pubsubs.
    """

    _r: redis.Redis
    _pubsub: RPubSub

    def __init__(self, subscribe_to: List[ChannelName] = []):
        """Create a pubsub object.

        Args:
            subscribe_to: A list of channels to listen for.
        """
        self._r = redis.Redis(**get_redis_host_and_port())
        self._pubsub = self._r.pubsub(ignore_subscribe_messages=True)
        self._pubsub.subscribe([str(channel_name) for channel_name in subscribe_to])

    def publish(self, channel_name: ChannelName, cmd: Command) -> None:
        """Publish a command to a channel."""
        self._r.publish(
            channel_name,
            json.dumps(cmd.to_dict()),
        )

    def listen(self) -> Iterable[Dict]:
        """Await and read updates from subscribed-to channels."""
        return self._pubsub.listen()

    def get_message(self, timeout: float = 0.0) -> Dict:
        """Get the next available message from subscribed-to pubsubs."""
        return self._pubsub.get_message(timeout=timeout, ignore_subscribe_messages=True)

    def get_data_from_message(self, message: Dict) -> Dict:
        """Take a Redis-native message and parse its data as a Python dict."""
        return json.loads(message["data"].decode("utf-8"))

    def get_channel_from_message(self, message: Message) -> ChannelName:
        """Get the channel name from a Redis-native message."""
        return ChannelName(message["channel"].decode("utf-8"))  # type: ignore
