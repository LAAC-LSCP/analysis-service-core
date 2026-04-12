from uuid import UUID

from analysis_service_core.src.redis.commands import (
    CompleteTask,
    Operation,
    ReportProgress,
    RunTask,
)


def test_run_task_to_dict_and_back():
    run_task = RunTask(
        task_id=UUID("ffaf6f54-3fc8-4aae-a156-3cc79ddc6aad"),
        dataset_uid_label="my-dataset_42b0a928-7647-40d4-ba3c-e03422d09aa8",
        operation=Operation.RUN_VTC_2,
    )

    assert RunTask.from_dict(run_task.to_dict()) == run_task


def test_complete_task_to_dict_and_back():
    complete_task = CompleteTask(
        task_id=UUID("5494be08-3f58-40a6-8c4d-8846184ee21b"),
    )

    assert CompleteTask.from_dict(complete_task.to_dict()) == complete_task


def test_report_progress_to_dict_and_back():
    report_progress = ReportProgress(
        task_id=UUID("22906f72-685a-43b4-9dc8-0c57aa1fafbc"),
        progress=0.135,
    )

    assert ReportProgress.from_dict(report_progress.to_dict()) == report_progress
