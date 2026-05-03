"""A mock for pubsubs, avoiding the need for network calls or a broker instance."""

from typing import Iterable, List

from analysis_service_core.src.redis.commands import Command
from analysis_service_core.src.redis.pubsub import ChannelName, Data, Message, PubSub


class PubSubMock(PubSub):
    """A mock for Redis pubsubs, without needing network calls or a Redis instance.

    For testing reasons, this mock acts closer to a queue than a pubsub.
    """

    _messages: List[Message]
    _channel_names: List[ChannelName]

    def __init__(
        self,
        subscribe_to: List[ChannelName] = [],
        messages: List[Message] = [],
    ):
        """Initialise a mock pubsub."""
        self._channel_names = subscribe_to
        self._messages = messages.copy()

    def publish(self, channel_name: ChannelName, cmd: Command) -> None:  # type: ignore
        """Append a command message to a mock channel."""
        self._messages.append(
            {
                "channel": channel_name,
                "data": cmd.to_dict(),  # type: ignore
            }
        )

    def get_message(self, timeout: float = 0.0) -> dict:
        """Forcefully pop a message from the pubsub."""
        if self._messages:
            return self._messages.pop(0)  # type: ignore
        return {}

    def listen(self) -> Iterable[Message]:  # type: ignore
        """Pop messages repeatedly from the pubsub."""
        while self._messages:
            yield self._messages.pop(0)

    def get_data_from_message(self, message) -> Data:  # type: ignore
        """."""
        return message["data"]

    def get_channel_from_message(self, message: Message) -> ChannelName:
        """Get the channel from a Redis-py message."""
        return ChannelName(message["channel"])
