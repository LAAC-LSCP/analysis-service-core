from abc import ABC
from dataclasses import dataclass
from typing import Literal
from uuid import UUID


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
    operation: Literal["vtc"]

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
