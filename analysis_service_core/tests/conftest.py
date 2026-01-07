import shutil
from pathlib import Path
from typing import Protocol
from uuid import UUID

import pytest


class TempDatasetFactory(Protocol):
    def __call__(self, dataset_uid: UUID) -> Path: ...


@pytest.fixture(scope="session")
def temp_dataset_factory(
    tmp_path_factory: pytest.TempPathFactory,
) -> TempDatasetFactory:
    """
    Factory to create temporary datasets
    """

    def create_temp_dataset(dataset_uid: UUID) -> Path:
        dataset_dir = (Path(__file__) / ".." / "datasets" / str(dataset_uid)).resolve()

        assert dataset_dir.exists()

        temp_dir = tmp_path_factory.mktemp("datasets")
        temp_dataset_dir = temp_dir / str(dataset_uid)

        shutil.copytree(dataset_dir, temp_dataset_dir)

        return temp_dataset_dir

    return create_temp_dataset
