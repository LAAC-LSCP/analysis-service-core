import json
from pathlib import Path
from uuid import UUID

import pytest

from analysis_service_core.src.redis.commands import (
    Command,
    CompleteTask,
    Operation,
    ReportProgress,
    RunTask,
)


@pytest.mark.parametrize(
    "command",
    [
        RunTask(
            task_id=UUID("ffaf6f54-3fc8-4aae-a156-3cc79ddc6aad"),
            dataset_uid_label="my-dataset_42b0a928-7647-40d4-ba3c-e03422d09aa8",
            operation=Operation.RUN_VTC_2,
        ),
        RunTask(
            task_id=UUID("ffaf6f54-3fc8-4aae-a156-3cc79ddc6aad"),
            dataset_uid_label="my-dataset_42b0a928-7647-40d4-ba3c-e03422d09aa8",
            operation=Operation.RUN_VTC_2,
            directory=Path("/my/dataset/subdir"),
        ),
        RunTask(
            task_id=UUID("ffaf6f54-3fc8-4aae-a156-3cc79ddc6aad"),
            dataset_uid_label="my-dataset_42b0a928-7647-40d4-ba3c-e03422d09aa8",
            operation=Operation.RUN_VTC_2,
            resume=False,
        ),
        RunTask(
            task_id=UUID("ffaf6f54-3fc8-4aae-a156-3cc79ddc6aad"),
            dataset_uid_label="my-dataset_42b0a928-7647-40d4-ba3c-e03422d09aa8",
            operation=Operation.RUN_VTC_2,
            directory=Path("/my/dataset/subdir"),
            resume=False,
        ),
        CompleteTask(
            task_id=UUID("5494be08-3f58-40a6-8c4d-8846184ee21b"),
        ),
        ReportProgress(
            task_id=UUID("22906f72-685a-43b4-9dc8-0c57aa1fafbc"),
            completed_progress=0.10,
            completed_pass_effort=12.0,
            partial_pass_progress=0.12,
            partial_pass_effort=10.0,
            total_effort=100.0,
            completed_passes=10,
            total_passes=20,
        ),
    ],
)
class TestCommandSerialization:
    """Test command serialization and deserialization."""

    def test_to_dict_and_back(self, command: Command):
        """Test command serialization to dict and back."""
        assert type(command).from_dict(command.to_dict()) == command

    def test_json_round_trip(self, command: Command):
        """Test JSON serialization round trip for commands cross-service style."""
        json_str = json.dumps(command.to_dict())
        loaded_dict = json.loads(json_str)
        reconstructed = type(command).from_dict(loaded_dict)

        assert reconstructed == command
