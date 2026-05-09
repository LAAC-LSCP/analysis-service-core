"""Base class for E2E model tests using Docker containers and Redis."""

import shutil
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Optional, Type
from uuid import UUID, uuid4

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.image import DockerImage
from testcontainers.core.network import Network
from testcontainers.redis import RedisContainer

from analysis_service_core.src.config import Config
from analysis_service_core.src.effort_model import EffortModel
from analysis_service_core.src.filesystem import get_dataset_dir, get_final_output_dir
from analysis_service_core.src.logger import LoggerFactory
from analysis_service_core.src.redis.commands import (
    CompleteTask,
    Operation,
    ReportProgress,
    RunTask,
)
from analysis_service_core.src.redis.core_types import RedisInfo
from analysis_service_core.src.redis.pubsub import ChannelName, PubSub
from analysis_service_core.src.redis.queue import Queue, QueueName

_TASK_ID = UUID("00000000-0000-0000-0000-000000000001")
logger = LoggerFactory.get_logger(__name__)


@contextmanager
def _progress_collector(pubsub: PubSub, collected: List[ReportProgress]) -> Generator:
    stop_event = threading.Event()

    def _collect() -> None:
        while not stop_event.is_set():
            msg = pubsub.get_message(timeout=1.0)
            if msg is None:
                continue
            collected.append(
                ReportProgress.from_dict(pubsub.get_data_from_message(msg))
            )

    collector = threading.Thread(target=_collect, daemon=True)
    collector.start()
    try:
        yield
    finally:
        time.sleep(0.5)
        stop_event.set()
        collector.join(timeout=5)


def _collect_tree(root: Path) -> set:
    return {p.relative_to(root) for p in root.rglob("*") if p.is_file()}


class ModelE2ETestBase:
    """Base class for E2E model tests.

    Spins up Redis and the worker Docker container, enqueues a RunTask on the
    model's queue, waits for a CompleteTask, then verifies output files and
    progress messages.

    Progress is collected by subscribing to the UPDATE_STATUS pub/sub channel
    in a background thread before the task starts, so no messages are missed.

    Redis must be running before any Queue or PubSub is instantiated — the
    fixture handles this ordering: containers first, then queues and pubsub.

    Subclasses must set: queue_name, operation, dockerfile, worker_env,
    datasets_dir, echolalia_dir, DATASET_UID.
    """

    pytestmark = pytest.mark.e2e

    queue_name: QueueName
    operation: Operation
    dockerfile: Path
    worker_env: dict
    datasets_dir: Path
    echolalia_dir: Path
    build_context: Optional[Path] = None  # defaults to dockerfile.parent
    extra_volume_mounts: list[tuple[Path, str]] = []

    effort_model_cls: Type[EffortModel]
    config: Config

    TIMEOUT: int = 1_000
    DATASET_UID: UUID
    SUBDIRECTORY: Optional[str] = None
    TEST_IDEMPOTENCY: bool = False

    _progress_messages: List[ReportProgress]
    _output_dir: Path
    _dataset_after_first_run: set
    _dataset_after_second_run: set
    _effort_model: EffortModel
    _datasets_tmp: Path

    @pytest.fixture(autouse=True, scope="class")
    def setup_e2e(
        self, request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
    ):
        """Spin up Redis and the worker container, run the task, collect results."""
        logger.info("Setting up E2E test environment")
        tmp_path = tmp_path_factory.mktemp("e2e")
        datasets_tmp = tmp_path / "datasets"
        logger.info("Copying dataset into temporary workspace")
        shutil.copytree(
            self.datasets_dir / str(self.DATASET_UID),
            datasets_tmp / str(self.DATASET_UID),
        )

        output_dir = get_final_output_dir(
            get_dataset_dir(datasets_tmp, str(self.DATASET_UID)), _TASK_ID
        )
        collected: List[ReportProgress] = []

        effort_model = self.effort_model_cls(config=self.config)

        with Network() as network:
            logger.info("Starting Redis and worker test containers")
            self._run_with_network(network, datasets_tmp, output_dir, collected)

        cls = request.cls

        if cls is None:
            pytest.fail("Class-scoped fixture requires a test class")

        cls._output_dir = output_dir
        cls._progress_messages = collected
        cls._effort_model = effort_model
        cls._datasets_tmp = datasets_tmp

        yield

    def _run_with_network(
        self,
        network: Network,
        datasets_tmp: Path,
        output_dir: Path,
        collected: List[ReportProgress],
    ) -> None:
        with (
            RedisContainer().with_network(network).with_network_aliases("redis")
        ) as redis:
            logger.info("Redis container is ready")
            redis_info: RedisInfo = {
                "host": redis.get_container_host_ip(),
                "port": redis.get_exposed_port(6379),
            }

            run_queue = Queue(self.queue_name, redis_info=redis_info)
            completion_queue = Queue(QueueName.COMPLETE_TASK, redis_info=redis_info)
            pubsub = PubSub(
                subscribe_to=[ChannelName.UPDATE_STATUS], redis_info=redis_info
            )

            with _progress_collector(pubsub, collected):
                context = self.build_context or self.dockerfile.parent
                dockerfile_path = self.dockerfile.relative_to(context)

                logger.info("Building worker image")
                with DockerImage(
                    path=str(context),
                    dockerfile_path=str(dockerfile_path),
                    tag=f"analysis-service-e2e:{uuid4().hex}",
                ) as image:
                    logger.info("Running worker container")
                    self._run_with_image(
                        image,
                        network,
                        datasets_tmp,
                        output_dir,
                        run_queue,
                        completion_queue,
                    )

    def _run_with_image(
        self,
        image: DockerImage,
        network: Network,
        datasets_tmp: Path,
        output_dir: Path,
        run_queue: Queue,
        completion_queue: Queue,
    ) -> None:
        env = {
            "REDIS_HOST": "redis",
            "REDIS_PORT": "6379",
            "DATASETS_DIR": "/app/datasets",
            "ECHOLALIA_DIR": "/app/echolalia",
            **{k: str(v) for k, v in self.worker_env.items()},
        }

        def _run_task() -> None:
            logger.info("Starting container and enqueuing task")
            container = (
                DockerContainer(str(image))
                .with_network(network)
                .with_envs(**env)
                .with_volume_mapping(str(datasets_tmp), "/app/datasets", "rw")
                .with_volume_mapping(str(self.echolalia_dir), "/app/echolalia")
            )
            for host_path, container_path in self.extra_volume_mounts:
                container = container.with_volume_mapping(
                    str(host_path), container_path
                )
            with container:
                run_queue.enqueue(
                    RunTask(
                        task_id=_TASK_ID,
                        dataset_uid_label=str(self.DATASET_UID),
                        operation=self.operation,
                        directory=(
                            Path(self.SUBDIRECTORY) if self.SUBDIRECTORY else None
                        ),
                    )
                )
                logger.info("Waiting for task completion")
                self._await_completion(completion_queue)

        _run_task()

        if self.TEST_IDEMPOTENCY:
            logger.info("Running idempotency check")
            dataset_after_first_run = _collect_tree(output_dir)
            _run_task()
            self.__class__._dataset_after_first_run = dataset_after_first_run
            self.__class__._dataset_after_second_run = _collect_tree(output_dir)

    def _await_completion(self, queue: Queue) -> None:
        deadline = time.time() + self.TIMEOUT
        while time.time() < deadline:
            msg = queue.dequeue()
            if msg and CompleteTask.from_dict(msg).task_id == _TASK_ID:
                logger.info("Task completion received")
                return
            time.sleep(1)
        pytest.fail(f"Task did not complete within {self.TIMEOUT}s")

    def test_expected_output_files_exist(self) -> None:
        """Assert all expected output files exist based on the effort model."""
        assert self._output_dir.exists()

        dataset_dir = get_dataset_dir(self._datasets_tmp, str(self.DATASET_UID))

        # Collect all expected output files from all igroups
        expected_outputs = set()
        for igroup in self._effort_model.find_sorted_igroups(dataset_dir):
            pogroup = self._effort_model.pogroup_from_igroup(
                dataset_dir, self._output_dir, igroup
            )
            ogroup = self._effort_model.ogroup_from_pogroup(
                dataset_dir, self._output_dir, pogroup, igroup
            )
            for output_file in ogroup:
                expected_outputs.add(output_file.relative_to(self._output_dir))

        missing_files = [
            f for f in expected_outputs if not (self._output_dir / f).exists()
        ]
        assert not missing_files, f"Expected output files missing: {missing_files}"

    def test_metannots_created(self) -> None:
        """Assert metannots.yml was written to the output directory."""
        assert (self._output_dir / "metannots.yml").exists()

    def test_progress_received(self) -> None:
        """Assert at least one progress message was published."""
        assert len(self._progress_messages) > 0

    def test_progress_completes(self) -> None:
        """Assert the final progress message reports all passes complete."""
        last = self._progress_messages[-1]
        assert last.completed_passes == last.total_passes

    def test_idempotent(self) -> None:
        """Assert the output file tree is identical after a second run."""
        if not self.TEST_IDEMPOTENCY:
            pytest.skip("TEST_IDEMPOTENCY not enabled")
        assert self._dataset_after_first_run == self._dataset_after_second_run
