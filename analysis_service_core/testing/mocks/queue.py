"""A mock for queues, avoiding the need for network calls or a broker instance."""

from typing import List, Optional

from analysis_service_core.src import errors
from analysis_service_core.src.redis.commands import Command
from analysis_service_core.src.redis.queue import Queue, QueueName


class QueueMock(Queue):
    """A mock implementation of a message queue for testing purposes.

    This class simulates basic queue operations such as enqueue and dequeue,
    storing messages in memory. It is useful for unit tests where interaction
    with a real external queue is not required.
    """

    _name: QueueName
    _messages: List[dict]

    def __init__(self, name: QueueName, messages: Optional[List[dict]] = None):
        """Instantiate a mock queue.

        Args:
            name: The queue name.
            messages: The list of messages pre-existing in the queue.
        """
        self._name = name
        self._messages = messages.copy() if messages else []

    def enqueue(self, cmd: Command) -> None:
        """Add an item to the queue."""
        try:
            self._messages.append(cmd.to_dict())
        except Exception as e:
            raise errors.QueuePushFailed(str(self._name)) from e

    def dequeue(self) -> Optional[dict]:
        """Remove an item from the queue."""
        if self._messages:
            try:
                return self._messages.pop(0)
            except Exception as e:
                raise errors.QueuePopFailed(str(self._name)) from e
        return None
