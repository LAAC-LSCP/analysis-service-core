from pathlib import Path
from typing import Optional, Protocol, Tuple
from uuid import UUID

import pytest
from pytest import TempPathFactory

from analysis_service_core.src.config import Config
from analysis_service_core.src.redis.queue import QueueName
from analysis_service_core.testing.mocks.pubsub import PubSubMock
from analysis_service_core.testing.mocks.queue import QueueMock
from analysis_service_core.testing.models import WordCountEffortModel, WordCountModel
from analysis_service_core.tests.conftest import TempDatasetFactory


class WordCountModelFactory(Protocol):
    def __call__(
        self,
        dataset_uid: UUID,
        task_uid: UUID,
        pubsub_mock: Optional[PubSubMock] = None,
        use_model_output_folder: bool = True,
    ) -> Tuple[WordCountModel, PubSubMock, Path, Path, UUID, UUID, Config]: ...


@pytest.fixture
def word_count_model_factory(
    temp_dataset_factory: TempDatasetFactory, tmp_path_factory: TempPathFactory
) -> WordCountModelFactory:
    """
    Fixture that provides a factory function for creating a WordCountModel and its test
    environment.

    The factory sets up a temporary dataset, output directories, and a mock queue,
    returning all necessary objects for integration testing the WordCountModel. This
    way parameterized tests can create isolated model instances with different
    configurations.
    """

    def _create_word_count_model(
        dataset_uid: UUID,
        task_uid: UUID,
        pubsub_mock: Optional[PubSubMock] = None,
        use_model_output_folder: bool = True,
    ) -> Tuple[WordCountModel, PubSubMock, Path, Path, UUID, UUID, Config]:
        temp_dataset = temp_dataset_factory(dataset_uid=dataset_uid)
        temp_echolalia_dir = tmp_path_factory.mktemp("echolalia_dir")

        if use_model_output_folder:
            model_output_folder = tmp_path_factory.mktemp("word-count-output")
        else:
            model_output_folder = None

        queue_mock = QueueMock(
            messages=[
                {
                    "task_id": str(task_uid),
                    "dataset_uid_label": str(dataset_uid),
                    "operation": "word-count",
                }
            ],
            name="RUN_WORD_COUNT_MODEL",  # type: ignore
        )

        config = Config(check_required=False)

        config.set("DATASETS_DIR", temp_dataset.parent)
        config.set("ECHOLALIA_DIR", temp_echolalia_dir)
        pubsub_mock = pubsub_mock or PubSubMock()

        return (
            WordCountModel(
                queue=queue_mock,  # type: ignore
                config=config,
                effort_model=WordCountEffortModel(config),
                pubsub=pubsub_mock,
                model_output_folder=model_output_folder,
                _completion_queue=QueueMock(name=QueueName.COMPLETE_TASK),
                _progress_queue=QueueMock(name=QueueName.PROGRESS),
            ),
            pubsub_mock,
            temp_dataset,
            temp_dataset.parent,
            dataset_uid,
            task_uid,
            config,
        )

    return _create_word_count_model
