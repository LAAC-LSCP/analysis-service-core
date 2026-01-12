from typing import List, Optional

from analysis_service_core.src.redis.commands import Command
from analysis_service_core.src.redis.queue import QueueName


class QueueMock:
    _name: QueueName
    _messages: List[dict]

    def __init__(self, name: QueueName, messages: Optional[List[dict]] = None):
        self._name = name
        self._messages = messages.copy() if messages else []

    def enqueue(self, cmd: Command) -> None:
        self._messages.append(cmd.to_dict())

    def dequeue(self) -> Optional[dict]:
        if self._messages:
            return self._messages.pop(0)
        return None
