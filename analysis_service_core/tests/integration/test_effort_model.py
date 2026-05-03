from uuid import UUID

import pytest

from analysis_service_core.tests.integration.conftest import WordCountModelFactory
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
    progress = wc_effort_model.get_progress(dataset_dir, task_uid)
    assert progress["completed_progress"] == 0.0
    assert progress["partial_pass_progress"] == 0.0

    model.run()

    progress = wc_effort_model.get_progress(dataset_dir, task_uid)
    assert progress["completed_progress"] == 1.0
    assert progress["partial_pass_progress"] == 1.0


def test_wc_effort_model_step_by_step(
    word_count_model_factory: WordCountModelFactory,
):
    """
    Mimics the ModelPlugin.run() loop igroup by igroup.

    For each igroup: calls run_model, verifies all pass output files are written to
    disk, then calls postprocess. Checks that completed_progress and completed_passes
    increment correctly after each full step.

    effort per igroup: words_1_1 (3.5), words_1_2 (3.5), words_2_1 (4.5) = 11.5 total
    """
    dataset_uuid = UUID("51088a18-6c2a-4e65-ae00-8b62d86fe66e")
    task_uuid = UUID("45d59e06-f163-4dea-b8c5-6e3aa3413009")

    model, _, dataset_dir, _, _, task_uid = word_count_model_factory(
        dataset_uuid, task_uuid, use_model_output_folder=False
    )

    wc_effort_model = WordCountEffortModel()
    output_dir = dataset_dir / "outputs" / str(task_uid)

    progress = wc_effort_model.get_progress(dataset_dir, task_uid)
    assert progress["completed_progress"] == 0.0
    assert progress["completed_passes"] == 0
    assert progress["total_passes"] == 3

    TASK_EFFORT = 11.5
    igroups = sorted(wc_effort_model.find_igroups(dataset_dir), key=lambda ig: ig[0])

    for i, (igroup, expected_effort) in enumerate(zip(igroups, [3.5, 7.0, 11.5])):
        model.run_model(dataset_dir, output_dir, igroup)

        pogroup = wc_effort_model.pogroup_from_igroup(dataset_dir, output_dir, igroup)
        for f in pogroup:
            assert f.exists(), f"Expected pass output {f} to exist after run_model"

        model.postprocess(dataset_dir, output_dir, pogroup, igroup)

        progress = wc_effort_model.get_progress(dataset_dir, task_uid)
        assert progress["completed_progress"] == pytest.approx(
            expected_effort / TASK_EFFORT
        )
        assert progress["completed_passes"] == i + 1
