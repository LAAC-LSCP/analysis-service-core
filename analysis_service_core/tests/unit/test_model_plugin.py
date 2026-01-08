from pathlib import Path
from typing import Protocol, Tuple
from uuid import UUID

import pytest
from pytest import TempPathFactory

from analysis_service_core.src.config import Config
from analysis_service_core.testing.mocks.pubsub import PubSubMock
from analysis_service_core.tests.conftest import TempDatasetFactory
from analysis_service_core.tests.models.word_count_model import WordCountModel


@pytest.mark.parametrize(
    "dataset_uuid,task_uuid,use_model_output_folder",
    [
        (
            "51088a18-6c2a-4e65-ae00-8b62d86fe66e",
            "98b4279b-c201-454a-8a3c-20c06fbf86f1",
            True,
        ),
        (
            "51088a18-6c2a-4e65-ae00-8b62d86fe66e",
            "6906ebf8-2836-484a-9420-7923e1a3f79c",
            False,
        ),
    ],
)
def test_word_count_model_run(
    word_count_model_factory: "WordCountModelFactory",
    dataset_uuid: str,
    task_uuid: str,
    use_model_output_folder: bool,
):
    model, _, echolalia_dir, dataset_uid, task_uid = word_count_model_factory(
        UUID(dataset_uuid), UUID(task_uuid), use_model_output_folder
    )
    model.run()

    outputs = {f for f in echolalia_dir.rglob("*.txt")}
    output_file = (
        echolalia_dir
        / "outputs"
        / str(dataset_uid)
        / str(task_uid)
        / "child_1"
        / "words_1_1.txt"
    )
    assert outputs == {
        output_file,
        echolalia_dir
        / "outputs"
        / str(dataset_uid)
        / str(task_uid)
        / "child_1"
        / "words_1_2.txt",
        echolalia_dir
        / "outputs"
        / str(dataset_uid)
        / str(task_uid)
        / "child_2"
        / "words_2_1.txt",
    }

    content = output_file.read_text()
    assert content == "Word count: 14\n"


class WordCountModelFactory(Protocol):
    def __call__(
        self, dataset_uid: UUID, task_uid: UUID, use_model_output_folder: bool = True
    ) -> Tuple[WordCountModel, Path, Path, UUID, UUID]: ...


@pytest.fixture(scope="module")
def word_count_model_factory(
    temp_dataset_factory: TempDatasetFactory, tmp_path_factory: TempPathFactory
) -> WordCountModelFactory:
    def _create_word_count_model(
        dataset_uid: UUID, task_uid: UUID, use_model_output_folder: bool = True
    ) -> Tuple[WordCountModel, Path, Path, UUID, UUID]:
        temp_dataset = temp_dataset_factory(dataset_uid=dataset_uid)
        temp_echolalia_dir = tmp_path_factory.mktemp("echolalia_dir")

        if use_model_output_folder:
            model_output_folder = tmp_path_factory.mktemp("word-count-output")
        else:
            model_output_folder = None

        pubsub_mock = PubSubMock(
            subscribe_to=["RUN_WORD_COUNT_MODEL"],  # type: ignore
            messages=[
                {
                    "channel_name": "RUN_WORD_COUNT_MODEL",  # type: ignore
                    "data": {
                        "task_id": str(task_uid),
                        "dataset_uid_label": f"my-dataset_{str(dataset_uid)}",
                        "operation": "word-count",
                    },
                }
            ],
        )

        config = Config(check_required=False)

        config.set("DATASETS_DIR", temp_dataset.parent)
        config.set("ECHOLALIA_DIR", temp_echolalia_dir)

        return (
            WordCountModel(
                pubsub=pubsub_mock,  # type: ignore
                model_output_folder=model_output_folder,
                config=config,
            ),
            temp_dataset,
            temp_echolalia_dir,
            dataset_uid,
            task_uid,
        )

    return _create_word_count_model
