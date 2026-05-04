"""Filesystem helpers relating to tasks."""

from pathlib import Path
from uuid import UUID


def get_final_output_dir(dataset_dir: Path, task_id: UUID) -> Path:
    """Receive the output directory of the task inside the dataset."""
    return dataset_dir / "outputs" / str(task_id)


def uid_label_to_uid(uid_label: str) -> UUID:
    """Take a uid label pair and extract the uid label."""
    return UUID(hex=uid_label.split("_")[-1])


def get_dataset_dir(datasets_dir: Path, uid_label: str) -> Path:
    """Find the dataset directory inside the datasets directory."""
    dataset_uid = uid_label_to_uid(uid_label)

    return datasets_dir / str(dataset_uid)
