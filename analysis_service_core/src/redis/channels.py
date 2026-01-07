from dataclasses import dataclass
from enum import StrEnum
from typing import Set, Type

from analysis_service_core.src.redis import commands


class ChannelName(StrEnum):
    COMPLETE_TASK = "complete_task"
    RUN_VTC = "run_vtc"


@dataclass(frozen=True)
class ChannelDict:
    name: ChannelName
    command: Type[commands.Command]


class Channels:
    """
    Wrapper for Redis channel management
    """

    _channels: Set[ChannelDict]

    def __init__(self, channels: Set[ChannelDict]):
        self._channels = channels

    @property
    def channel_names(self) -> Set[str]:
        return {channel.name for channel in self._channels}

    @property
    def events(self) -> Set[Type[commands.Command]]:
        return {channel.command for channel in self._channels}

    @property
    def channels(self) -> Set[ChannelDict]:
        return self._channels


def get_channels() -> Channels:
    return Channels(
        {
            ChannelDict(
                name=ChannelName.RUN_VTC,
                command=commands.RunTask,
            ),
            ChannelDict(
                name=ChannelName.COMPLETE_TASK,
                command=commands.CompleteTask,
            ),
        }
    )
