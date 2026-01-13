from abc import ABC
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from analysis_service_core.src import errors


# TODO: "Operation" is the same as "model". Want to rename this
# entire class at a later point to `Model`
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

    @classmethod
    def from_dict(self, dict_repr: dict) -> "Command":
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

    @classmethod
    def from_dict(self, dict_repr: dict) -> "RunTask":
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

    @classmethod
    def from_dict(self, dict_repr: dict) -> "CompleteTask":
        return CompleteTask(
            task_id=UUID(dict_repr["task_id"]),
        )
