from typing import Dict, Iterable, List, TypeAlias, TypedDict

from analysis_service_core.src.redis.commands import Command
from analysis_service_core.src.redis.pubsub import ChannelName, PubSub

Data: TypeAlias = Dict


class Message(TypedDict):
    channel: ChannelName
    data: Data


class PubSubMock(PubSub):
    _messages: List[Message]
    _channel_names: List[ChannelName]

    def __init__(
        self,
        subscribe_to: List[ChannelName] = [],
        messages: List[Message] = [],
    ):
        self._channel_names = subscribe_to
        self._messages = messages.copy()

    def publish(self, channel_name: ChannelName, cmd: Command) -> None:  # type: ignore
        self._messages.append(
            {
                "channel": channel_name,
                "data": cmd.to_dict(),  # type: ignore
            }
        )

    def get_message(self, timeout: float = 0.0) -> dict:
        if self._messages:
            return self._messages.pop(0)  # type: ignore
        return {}

    def listen(self) -> Iterable[Message]:  # type: ignore
        while self._messages:
            yield self._messages.pop(0)

    def get_data_from_message(self, message) -> Data:  # type: ignore
        return message["data"]

    def get_channel_from_message(self, message: dict) -> ChannelName:
        return ChannelName(message["channel"])
