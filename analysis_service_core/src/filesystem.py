"""Filesystem helpers relating to tasks."""

from pathlib import Path
from uuid import UUID


def get_final_output_dir(dataset_dir: Path, task_id: UUID) -> Path:
    """Receive the output directory of the task inside the dataset."""
    return dataset_dir / "outputs" / str(task_id)


def get_dataset_dir(datasets_dir: Path, uid_label: str) -> Path:
    """Find the dataset directory inside the datasets directory."""
    return datasets_dir / uid_label
