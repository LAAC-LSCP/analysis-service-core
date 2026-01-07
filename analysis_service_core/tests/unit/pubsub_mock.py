from typing import Iterable, List, TypedDict

from analysis_service_core.src.redis.channels import ChannelName
from analysis_service_core.src.redis.pubsub import PubSub


class Data(TypedDict):
    task_id: str
    dataset_uid_label: str
    operation: str


class Message(TypedDict):
    channel_name: ChannelName
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
        self._messages = messages

    def publish(self, _: ChannelName) -> None:  # type: ignore
        pass

    def listen(self) -> Iterable[Message]:  # type: ignore
        for message in self._messages:
            yield message

    def get_data_from_message(self, message) -> Data:  # type: ignore
        return message["data"]
