"""A collection of core helper types used for the Redis-based message broker."""

from typing import TypedDict


class RedisInfo(TypedDict):
    """Redis network information."""

    host: str
    port: int
