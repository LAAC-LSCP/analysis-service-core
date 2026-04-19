from uuid import UUID

from analysis_service_core.tests.integration.test_model_plugin import (
    WordCountModelFactory,
)
from analysis_service_core.tests.models.word_count_effort_model import (
    WordCountEffortModel,
)


def test_wc_effort_model(
    word_count_model_factory: WordCountModelFactory,
):
    dataset_uuid = UUID("51088a18-6c2a-4e65-ae00-8b62d86fe66e")
    task_uuid = UUID("7549b2ed-c0ed-448f-aae9-2b1c87aed255")

    model, _, dataset_dir, _, _, task_uid = word_count_model_factory(
        dataset_uuid, task_uuid, use_model_output_folder=False
    )

    wc_effort_model = WordCountEffortModel()
    assert wc_effort_model.get_progress(dataset_dir, task_uid)["progress"] == 0.0

    model.run()

    assert wc_effort_model.get_progress(dataset_dir, task_uid)["progress"] == 1.0


def test_wc_effort_model_partial_progress(
    word_count_model_factory: WordCountModelFactory,
):
    dataset_uuid = UUID("51088a18-6c2a-4e65-ae00-8b62d86fe66e")
    task_uuid = UUID("45d59e06-f163-4dea-b8c5-6e3aa3413009")

    model, _, dataset_dir, datasets_dir, dataset_uid, task_uid = (
        word_count_model_factory(dataset_uuid, task_uuid, use_model_output_folder=False)
    )

    wc_effort_model = WordCountEffortModel()
    assert wc_effort_model.get_progress(dataset_dir, task_uid)["progress"] == 0.0

    model.run()
    # Remove progress for words_1_1.txt, which has effort = 3 (i.e., 3 lines)
    (
        datasets_dir
        / str(dataset_uid)
        / "outputs"
        / str(task_uid)
        / "child_1"
        / "words_1_1.txt"
    ).unlink()

    assert wc_effort_model.get_progress(dataset_dir, task_uid)["progress"] == (
        3 + 4
    ) / (3 + 3 + 4)

    # Remove progress for words_2_1.txt, which has effort = 4 (i.e., 4 lines)
    (
        datasets_dir
        / str(dataset_uid)
        / "outputs"
        / str(task_uid)
        / "child_2"
        / "words_2_1.txt"
    ).unlink()

    assert wc_effort_model.get_progress(dataset_dir, task_uid)["progress"] == (3) / (
        3 + 3 + 4
    )
