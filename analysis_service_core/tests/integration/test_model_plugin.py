from typing import List
from uuid import UUID

import pytest

from analysis_service_core.src.redis.pubsub import ChannelName
from analysis_service_core.testing.mocks.pubsub import PubSubMock
from analysis_service_core.tests.integration.conftest import WordCountModelFactory


@pytest.mark.parametrize(
    "dataset_uuid,task_uuid,progresses,use_model_output_folder",
    [
        (
            "51088a18-6c2a-4e65-ae00-8b62d86fe66e",
            "98b4279b-c201-454a-8a3c-20c06fbf86f1",
            [0.4, 0.7, 1.0],
            True,
        ),
        (
            "51088a18-6c2a-4e65-ae00-8b62d86fe66e",
            "6906ebf8-2836-484a-9420-7923e1a3f79c",
            [0.4, 0.7, 1.0],
            False,
        ),
    ],
)
def test_word_count_model_run(
    word_count_model_factory: WordCountModelFactory,
    dataset_uuid: str,
    task_uuid: str,
    progresses: List[float],
    use_model_output_folder: bool,
):
    model, pubsub_mock, dataset_dir, datasets_dir, dataset_uid, task_uid = (
        word_count_model_factory(
            UUID(dataset_uuid),
            UUID(task_uuid),
            pubsub_mock=PubSubMock(subscribe_to=[ChannelName.UPDATE_STATUS]),
            use_model_output_folder=use_model_output_folder,
        )
    )
    model.run()

    outputs = {f for f in (dataset_dir / "outputs").rglob("*.txt")}
    output_file = (
        datasets_dir
        / str(dataset_uid)
        / "outputs"
        / str(task_uid)
        / "child_1"
        / "words_1_1.txt"
    )
    assert outputs == {
        output_file,
        datasets_dir
        / str(dataset_uid)
        / "outputs"
        / str(task_uid)
        / "child_1"
        / "words_1_2.txt",
        datasets_dir
        / str(dataset_uid)
        / "outputs"
        / str(task_uid)
        / "child_2"
        / "words_2_1.txt",
    }

    messages = list(map(pubsub_mock.get_message, range(len(progresses))))
    data = list(map(pubsub_mock.get_data_from_message, messages))

    assert [{"task_id": d["task_id"], "progress": d["progress"]} for d in data] == [
        {"task_id": str(task_uuid), "progress": progress} for progress in progresses
    ]
