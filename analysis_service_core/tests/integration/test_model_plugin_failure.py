from pathlib import Path
from uuid import UUID

from analysis_service_core.src.config import Config
from analysis_service_core.src.effort_model import InputGroup, PassOutputGroup
from analysis_service_core.src.model import ModelPlugin
from analysis_service_core.src.redis.commands import FailTask
from analysis_service_core.src.redis.queue import QueueName
from analysis_service_core.testing.mocks.pubsub import PubSubMock
from analysis_service_core.testing.mocks.queue import QueueMock
from analysis_service_core.testing.models import WordCountEffortModel
from analysis_service_core.tests.conftest import TempDatasetFactory

_DATASET_UUID = UUID("51088a18-6c2a-4e65-ae00-8b62d86fe66e")
_TASK_UUID = UUID("98b4279b-c201-454a-8a3c-20c06fbf86f1")


class AlwaysFailsModel(ModelPlugin):
    """A model double whose run_model always raises, for failure-path testing."""

    def run_model(
        self, dataset_dir: Path, output_dir: Path, igroup: InputGroup
    ) -> None:
        raise RuntimeError("simulated model failure")

    def postprocess(
        self,
        dataset_dir: Path,
        output_dir: Path,
        pogroup: PassOutputGroup,
        igroup: InputGroup,
    ) -> None:
        pass


def _build_queues(task_uid: UUID, dataset_uid: UUID) -> dict:
    return {
        "queue": QueueMock(
            name=QueueName.RUN_TEST_MODEL,
            messages=[
                {
                    "task_id": str(task_uid),
                    "dataset_uid_label": str(dataset_uid),
                    "operation": "word-count",
                }
            ],
        ),
        "_completion_queue": QueueMock(name=QueueName.COMPLETE_TASK),
        "_fail_queue": QueueMock(name=QueueName.FAIL_TASK),
        "_progress_queue": QueueMock(name=QueueName.PROGRESS),
    }


def test_all_igroups_failing_publishes_fail_task(
    temp_dataset_factory: TempDatasetFactory,
):
    dataset_dir = temp_dataset_factory(dataset_uid=_DATASET_UUID)
    config = Config(check_required=False)
    config.set("DATASETS_DIR", dataset_dir.parent)
    config.set("ECHOLALIA_DIR", dataset_dir.parent)

    queues = _build_queues(_TASK_UUID, _DATASET_UUID)
    model = AlwaysFailsModel(
        queue=queues["queue"],
        config=config,
        effort_model=WordCountEffortModel(config),
        pubsub=PubSubMock(),
        _completion_queue=queues["_completion_queue"],
        _fail_queue=queues["_fail_queue"],
        _progress_queue=queues["_progress_queue"],
    )

    model.run()

    assert queues["_completion_queue"].dequeue() is None
    fail_message = queues["_fail_queue"].dequeue()
    assert fail_message is not None
    fail_task = FailTask.from_dict(fail_message)
    assert fail_task.task_id == _TASK_UUID
    assert "igroup" in fail_task.reason


def test_missing_dataset_dir_publishes_fail_task():
    config = Config(check_required=False)
    config.set("DATASETS_DIR", Path("/nonexistent"))
    config.set("ECHOLALIA_DIR", Path("/nonexistent"))

    queues = _build_queues(_TASK_UUID, _DATASET_UUID)
    model = AlwaysFailsModel(
        queue=queues["queue"],
        config=config,
        effort_model=WordCountEffortModel(config),
        pubsub=PubSubMock(),
        _completion_queue=queues["_completion_queue"],
        _fail_queue=queues["_fail_queue"],
        _progress_queue=queues["_progress_queue"],
    )

    model.run()

    assert queues["_completion_queue"].dequeue() is None
    fail_message = queues["_fail_queue"].dequeue()
    assert fail_message is not None
    assert FailTask.from_dict(fail_message).task_id == _TASK_UUID
