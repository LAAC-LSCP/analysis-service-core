"""A collection of domain-specific Exception subclasses."""


class RedisConnectionFailed(Exception):
    """Raised when a Redis connection cannot be made."""

    def __init__(self):
        """Initialize a RedisConnectionFailed exception."""
        super().__init__("Failed to establish a Redis connection")


class QueuePopFailed(Exception):
    """Raised when popping from a queue fails."""

    def __init__(self, queue_name: str):
        """Initialize a QueuePopFailed exception."""
        super().__init__(f"Failed to pop from queue: {queue_name}")
        self.queue_name = queue_name


class QueuePushFailed(Exception):
    """Raised when pushing to a queue fails."""

    def __init__(self, queue_name: str):
        """Initialize a QueuePushFailed exception."""
        super().__init__(f"Failed to push to queue: {queue_name}")
        self.queue_name = queue_name


class InvalidTaskFormat(Exception):
    """Raised when a task received is not in the expected format."""

    def __init__(self, dict_repr: dict):
        """Initialize a InvalidTaskFormat exception."""
        super().__init__(f"Invalid message format for: {str(dict_repr)}")
