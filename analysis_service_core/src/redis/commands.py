from abc import ABC
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Operation(StrEnum):
    RUN_VTC = "run_vtc"
    RUN_VTC_2 = "run_vtc_2"
    RUN_ALICE = "run_alice"
    RUN_W2V2 = "run_w2v2"
    RUN_ACOUSTICS = "run_acoustics"


class Command(ABC):
    task_id: UUID

    def to_dict(self) -> dict:
        raise NotImplementedError

    @classmethod
    def from_dict(self, dict_repr: dict) -> "Command":
        raise NotImplementedError


@dataclass
class RunTask(Command):
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
        return RunTask(
            task_id=UUID(dict_repr["task_id"]),
            dataset_uid_label=dict_repr["dataset_uid_label"],
            operation=dict_repr["operation"],
        )


@dataclass
class CompleteTask(Command):
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
