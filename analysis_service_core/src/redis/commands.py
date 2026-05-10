"""Utilities for commands.

Commands abstract messages through the message broker that
communicate actions to be taken.
"""

from abc import ABC
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Optional
from uuid import UUID

from analysis_service_core.src import errors


class Operation(StrEnum):
    """Operations that the service can perform."""

    RUN_VTC = "vtc"
    RUN_VTC_2 = "vtc_2"
    RUN_ALICE = "alice"
    RUN_W2V2 = "w2v2"
    RUN_ACOUSTICS = "acoustics"
    RUN_TEST_MODEL = "test_model"


class Command(ABC):
    """A generic class for wrapping commands.

    Commands in this context are pushed and pulled to and
    from queues, basically as a means for services to communicate.
    """

    task_id: UUID

    def to_dict(self) -> dict:
        """Convert a Command object to a dictionary."""
        raise NotImplementedError

    @staticmethod
    def from_dict(dict_repr: dict) -> "Command":
        """Convert a dictionary to a Command object."""
        raise NotImplementedError


@dataclass
class RunTask(Command):
    """`RunTask` commands encapsulate the action of running a task."""

    task_id: UUID
    dataset_uid_label: str
    operation: Operation
    directory: Optional[Path] = None
    resume: bool = True

    def to_dict(self) -> dict:
        """Convert a RunTask object to a dictionary."""
        return {
            "task_id": str(self.task_id),
            "dataset_uid_label": self.dataset_uid_label,
            "operation": str(self.operation),
            "directory": str(self.directory) if self.directory else None,
            "resume": self.resume,
        }

    @staticmethod
    def from_dict(dict_repr: dict) -> "RunTask":
        """Convert a dictionary to a RunTask object."""
        directory = None
        if dict_repr.get("directory"):
            directory = Path(dict_repr["directory"])

        try:
            return RunTask(
                task_id=UUID(dict_repr["task_id"]),
                dataset_uid_label=dict_repr["dataset_uid_label"],
                operation=dict_repr["operation"],
                directory=directory,
                resume=dict_repr.get("resume", True),
            )
        except Exception as e:
            raise errors.InvalidTaskFormat(dict_repr) from e


@dataclass
class CompleteTask(Command):
    """`CompleteTask` commands encapsulate the action of running a task."""

    task_id: UUID

    def to_dict(self) -> dict:
        """Convert a CompleteTask object to a dictionary."""
        return {
            "task_id": str(self.task_id),
        }

    @staticmethod
    def from_dict(dict_repr: dict) -> "CompleteTask":
        """Convert a dictionary to a CompleteTask object."""
        return CompleteTask(
            task_id=UUID(dict_repr["task_id"]),
        )


@dataclass
class ReportProgress(Command):
    """`ReportProgress` commands encapsulate the action of reporting task progress."""

    task_id: UUID
    completed_progress: float
    completed_pass_effort: float
    partial_pass_progress: float
    partial_pass_effort: float
    total_effort: float
    completed_passes: int
    total_passes: int

    def to_dict(self) -> dict:
        """Convert a ReportProgress object to a dictionary."""
        return {
            "task_id": str(self.task_id),
            "completed_progress": self.completed_progress,
            "completed_pass_effort": self.completed_pass_effort,
            "partial_pass_progress": self.partial_pass_progress,
            "partial_pass_effort": self.partial_pass_effort,
            "total_effort": self.total_effort,
            "completed_passes": self.completed_passes,
            "total_passes": self.total_passes,
        }

    @staticmethod
    def from_dict(dict_repr: dict) -> "ReportProgress":
        """Convert a dictionary to a ReportProgress object."""
        return ReportProgress(
            task_id=UUID(dict_repr["task_id"]),
            completed_progress=float(dict_repr["completed_progress"]),
            completed_pass_effort=float(dict_repr["completed_pass_effort"]),
            partial_pass_progress=float(dict_repr["partial_pass_progress"]),
            partial_pass_effort=float(dict_repr["partial_pass_effort"]),
            total_effort=float(dict_repr["total_effort"]),
            completed_passes=int(dict_repr["completed_passes"]),
            total_passes=int(dict_repr["total_passes"]),
        )
