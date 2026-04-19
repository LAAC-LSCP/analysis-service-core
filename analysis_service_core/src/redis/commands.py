from abc import ABC
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from analysis_service_core.src import errors


# TODO: "Operation" is the same as "model". Want to rename this
# entire class at a later point to `Model`
# TODO: maybe just remove operation. Seems like it's a relic from
# pubsub days when all models were listening on the same pubsub
class Operation(StrEnum):
    RUN_VTC = "vtc"
    RUN_VTC_2 = "vtc_2"
    RUN_ALICE = "alice"
    RUN_W2V2 = "w2v2"
    RUN_ACOUSTICS = "acoustics"


class Command(ABC):
    """
    A generic class for wrapping commands

    Commands in this context are pushed and pulled to and
    from queues, basically as a means for services to
    communicate
    """

    task_id: UUID

    def to_dict(self) -> dict:
        raise NotImplementedError

    @staticmethod
    def from_dict(dict_repr: dict) -> "Command":
        raise NotImplementedError


@dataclass
class RunTask(Command):
    """
    `RunTask` commands encapsulate the action of
    running a task
    """

    task_id: UUID
    dataset_uid_label: str
    operation: Operation

    def to_dict(self) -> dict:
        return {
            "task_id": str(self.task_id),
            "dataset_uid_label": self.dataset_uid_label,
            "operation": str(self.operation),
        }

    @staticmethod
    def from_dict(dict_repr: dict) -> "RunTask":
        try:
            return RunTask(
                task_id=UUID(dict_repr["task_id"]),
                dataset_uid_label=dict_repr["dataset_uid_label"],
                operation=dict_repr["operation"],
            )
        except Exception as e:
            raise errors.InvalidTaskFormat(dict_repr) from e


@dataclass
class CompleteTask(Command):
    """
    `CompleteTask` commands encapsulate the action of
    running a task
    """

    task_id: UUID

    def to_dict(self) -> dict:
        return {
            "task_id": str(self.task_id),
        }

    @staticmethod
    def from_dict(dict_repr: dict) -> "CompleteTask":
        return CompleteTask(
            task_id=UUID(dict_repr["task_id"]),
        )


@dataclass
class ReportProgress(Command):
    """
    `ReportProgress` commands encapsulate the action of
    reporting progress for a task
    """

    task_id: UUID
    # completed_effort / total_effort
    progress: float
    # completed_effort_w_partial_passes / total_effort
    partial_progress: float
    # effort expended thus far via completed model calls
    completed_effort: float
    # effort expended thus far via complete or incomplete model calls
    completed_effort_w_partial_passes: float
    # total effort required to finish the task
    total_effort: float

    def to_dict(self) -> dict:
        return {
            "task_id": str(self.task_id),
            "progress": self.progress,
            "partial_progress": self.partial_progress,
            "completed_effort": self.completed_effort,
            "completed_effort_w_partial_passes": self.completed_effort_w_partial_passes,
            "total_effort": self.total_effort,
        }

    @staticmethod
    def from_dict(dict_repr: dict) -> "ReportProgress":
        return ReportProgress(
            task_id=UUID(dict_repr["task_id"]),
            progress=float(dict_repr["progress"]),
            partial_progress=float(dict_repr["partial_progress"]),
            completed_effort=float(dict_repr["completed_effort"]),
            completed_effort_w_partial_passes=float(
                dict_repr["completed_effort_w_partial_passes"]
            ),
            total_effort=float(dict_repr["total_effort"]),
        )
