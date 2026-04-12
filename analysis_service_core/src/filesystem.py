from pathlib import Path
from uuid import UUID


def get_final_output_dir(dataset_dir: Path, task_id: UUID) -> Path:
    return dataset_dir / "outputs" / str(task_id)


def uid_label_to_uid(uid_label: str) -> UUID:
    return UUID(uid_label.split("_")[-1])


def get_dataset_dir(dataset_dir: Path, uid_label: str) -> Path:
    dataset_uid = uid_label_to_uid(uid_label)

    return dataset_dir / str(dataset_uid)
