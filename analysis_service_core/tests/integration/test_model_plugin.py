from typing import List
from uuid import UUID

import pytest

from analysis_service_core.src.effort_model import ProgressInfo
from analysis_service_core.src.redis.pubsub import ChannelName
from analysis_service_core.testing.mocks.pubsub import PubSubMock
from analysis_service_core.tests.integration.conftest import WordCountModelFactory

# task_effort = 3.5 (words_1_1) + 3.5 (words_1_2) + 4.5 (words_2_1) = 11.5
# effort per igroup = line_count + 0.5 (postprocess cost)
# Note: child_1/date.txt is shared between words_1_1 and words_1_2 pogroups,
# so after pass 1, pass 2 counts as partially started (effort_pogroup=3,
# effort_ogroup=0).
_EFFORT = 11.5
_EXPECTED_REPORTS: List[ProgressInfo] = [
    {
        "completed_progress": 3.5 / _EFFORT,
        "completed_pass_effort": 3.5,
        "partial_pass_progress": 3.5 / _EFFORT,
        "partial_pass_effort": 3.5,
        "total_effort": _EFFORT,
        "completed_passes": 1,
        "total_passes": 3,
    },
    {
        "completed_progress": 7.0 / _EFFORT,
        "completed_pass_effort": 7.0,
        "partial_pass_progress": 7.0 / _EFFORT,
        "partial_pass_effort": 7.0,
        "total_effort": _EFFORT,
        "completed_passes": 2,
        "total_passes": 3,
    },
    {
        "completed_progress": 1.0,
        "completed_pass_effort": _EFFORT,
        "partial_pass_progress": 1.0,
        "partial_pass_effort": _EFFORT,
        "total_effort": _EFFORT,
        "completed_passes": 3,
        "total_passes": 3,
    },
]


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
    word_count_model_factory: WordCountModelFactory,
    dataset_uuid: str,
    task_uuid: str,
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
    assert outputs == {
        datasets_dir
        / str(dataset_uid)
        / "outputs"
        / str(task_uid)
        / "child_1"
        / "words_1_1.txt",
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

    messages = list(map(pubsub_mock.get_message, range(len(_EXPECTED_REPORTS))))
    data = list(map(pubsub_mock.get_data_from_message, messages))

    assert [
        {k: d[k] for k in _EXPECTED_REPORTS[0] if k != "task_id"} for d in data
    ] == _EXPECTED_REPORTS
