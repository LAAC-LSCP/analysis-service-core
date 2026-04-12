from uuid import UUID

import pytest

from analysis_service_core.tests.integration.conftest import WordCountModelFactory


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
    model, dataset_dir, datasets_dir, dataset_uid, task_uid = word_count_model_factory(
        UUID(dataset_uuid), UUID(task_uuid), use_model_output_folder
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

    content = output_file.read_text()
    assert content == "Word count: 14\n"
