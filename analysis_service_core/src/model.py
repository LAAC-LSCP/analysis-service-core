"""This module contains `ModelPlugin` which handles the task lifecycle."""

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from time import sleep
from typing import List, Optional
from uuid import UUID

from analysis_service_core.src import errors
from analysis_service_core.src.config import Config
from analysis_service_core.src.effort_model import (
    EffortModel,
    InputGroup,
    PassOutputGroup,
    ProgressInfo,
)
from analysis_service_core.src.filesystem import get_dataset_dir, get_final_output_dir
from analysis_service_core.src.logger import Logger, LoggerFactory
from analysis_service_core.src.metannots import (
    DefaultMetannotsFactory,
    MetannotsFactory,
)
from analysis_service_core.src.redis.commands import (
    CompleteTask,
    FailTask,
    ReportProgress,
    RunTask,
)
from analysis_service_core.src.redis.pubsub import ChannelName, PubSub
from analysis_service_core.src.redis.queue import Queue, QueueName

_logger = LoggerFactory.get_logger(__name__)


class ModelPlugin(ABC):
    """Abstract base class for model plugins in the analysis service.

    Handles the full lifecycle of a task: polling a queue for incoming work,
    iterating over input groups, running the model and postprocessing per group,
    optionally moving outputs to a final location, and publishing a completion signal.

    Progress is tracked via an `EffortModel`, which defines how input groups map to
    pass outputs (pogroup) and final outputs (ogroup), and how effort is distributed
    across groups.

    Subclasses must implement:
        - `run_model(dataset_dir, output_dir, igroup)`: Execute the model on a single
            input group and write pass outputs to `output_dir`.
        - `postprocess(dataset_dir, output_dir, pogroup)`: Transform pass outputs into
            final outputs.

    Example:
        class MyModel(ModelPlugin):
            def run_model(
                self, dataset_dir: Path, output_dir: Path, igroup: InputGroup
            ) -> None:
                # subprocess call or model inference here
                pass

            def postprocess(
                self, dataset_dir: Path, output_dir: Path, pogroup: PassOutputGroup
            ) -> None:
                # move/rename/filter pass outputs into final form
                pass
    """

    _QUEUE_POLL_FREQ_S: int = 1
    _queue: Queue
    _completion_queue: Queue
    _fail_queue: Queue
    _progress_queue: Queue
    _pubsub: PubSub
    _config: Config
    _effort_model: EffortModel
    _logger: Logger
    _model_output_folder: Path | None = None
    _task_id: UUID | None = None
    _metannots_factory: MetannotsFactory

    def __init__(
        self,
        queue: Queue,
        config: Config,
        effort_model: EffortModel,
        pubsub: Optional[PubSub] = None,
        model_output_folder: Optional[Path] = None,
        metannots_factory: Optional[MetannotsFactory] = None,
        _completion_queue: Optional[Queue] = None,
        _fail_queue: Optional[Queue] = None,
        _progress_queue: Optional[Queue] = None,
    ):
        """Initialize the model plugin."""
        self._logger = _logger
        self._logger.info(f"Initialising {self.__class__.__name__}...")
        self._queue = queue
        self._model_output_folder = model_output_folder
        self._reset_output_folder()
        self._completion_queue = _completion_queue or Queue(QueueName.COMPLETE_TASK)
        self._fail_queue = _fail_queue or Queue(QueueName.FAIL_TASK)
        self._progress_queue = _progress_queue or Queue(QueueName.PROGRESS)
        self._pubsub = pubsub or PubSub(subscribe_to=[])
        self._config = config
        self._effort_model = effort_model
        self._metannots_factory = metannots_factory or DefaultMetannotsFactory()

    def _reset_output_folder(self) -> None:
        if self.model_output_folder is not None:
            shutil.rmtree(self.model_output_folder)
            self.model_output_folder.mkdir(parents=True)

    def run(self) -> None:
        """Block until a task received from the queue, then execute the task lifecycle.

        1. Dequeue a task and resolve the dataset and output directories.
        2. Discover input groups via the effort model.
        3. For each input group: run the model, verify pass outputs, postprocess,
           and report progress.
        4. Optionally move outputs to the final output location.
        5. Publish a completion or failure signal.

        Errors in individual igroup runs are logged and skipped; the task continues
        with remaining groups. If every igroup fails, or the task is aborted before
        any igroups could run, a failure signal is published instead of a completion
        signal. Any other unhandled error is reported as a failure and re-raised, so
        the underlying crash is still visible (e.g. in container logs/exit code).
        """
        command: dict = self._wait_for_message()

        # No task_id can be resolved from a malformed message, so there is nothing to
        # report a failure against; log and let this propagate.
        run_task = RunTask.from_dict(dict_repr=command)
        self._task_id = run_task.task_id
        self._logger = _logger.with_task(run_task.task_id).with_dataset(
            run_task.dataset_uid_label
        )

        try:
            self._run_task(run_task)
        except Exception as e:
            self._logger.exception("Unhandled error while running task.")
            self._fail(run_task.task_id, str(e))
            raise

    def _run_task(self, run_task: RunTask) -> None:
        dataset_dir = get_dataset_dir(
            self.config.dataset_dir, run_task.dataset_uid_label
        )

        if not dataset_dir.exists():
            message = f"Dataset directory not found: '{dataset_dir}'."
            self._logger.error(message)
            self._fail(run_task.task_id, message)
            return

        igroups = self._effort_model.find_sorted_igroups(dataset_dir)
        self._logger.info(f"Found {len(igroups)} total igroup(s).")
        output_dir = self._get_output_dir(run_task)

        igroups = self.filter_igroups(igroups, run_task.directory)
        if run_task.directory:
            self._logger.info(f"Filtered to {len(igroups)} igroup(s) within directory: \
{run_task.directory}")

        if run_task.resume:
            original_count = len(igroups)
            igroups = self._filter_incomplete_igroups(igroups, dataset_dir, output_dir)
            completed_count = original_count - len(igroups)
            if completed_count > 0:
                self._logger.info(
                    f"Resume mode: skipping {completed_count} completed igroup(s), \
{len(igroups)} remaining."
                )
            self._cleanup_incomplete_outputs(igroups, dataset_dir, output_dir)
            if len(igroups) > 0:
                self._logger.info(
                    f"Cleaned up incomplete outputs for {len(igroups)} igroup(s)."
                )

        failed_count = 0
        for idx, igroup in enumerate(igroups):
            self._logger.info(f"[{idx + 1}/{len(igroups)}] Processing igroup: {igroup}")
            try:
                self._run_on_igroup(dataset_dir, output_dir, igroup)
            except Exception:
                failed_count += 1
                self._logger.exception(
                    f"[{idx + 1}/{len(igroups)}] Failed to process igroup: {igroup}"
                )
                continue

        if igroups and failed_count == len(igroups):
            message = f"All {failed_count} igroup(s) failed to process."
            self._logger.error(message)
            self._fail(run_task.task_id, message)
            return

        if self.model_output_folder is not None:
            try:
                self._move_files(run_task)
            except Exception:
                self._logger.exception("Failed to move files to final output directory")

        try:
            self._create_metannots(run_task)
        except Exception:
            self._logger.exception("Failed to create metannots.yml")

        self._logger.info("Completed. Publishing completion signal.")
        self._completion_queue.enqueue(CompleteTask(task_id=run_task.task_id))

    def _fail(self, task_id: UUID, reason: str) -> None:
        """Publish a failure signal for the current task, best-effort."""
        try:
            self._fail_queue.enqueue(FailTask(task_id=task_id, reason=reason))
        except Exception:
            self._logger.exception("Failed to publish failure signal.")

    def filter_igroups(
        self, igroups: list[InputGroup], directory: Optional[Path] = None
    ) -> list[InputGroup]:
        """Filter input groups to only include those within the specified directory.

        Args:
            igroups: List of input groups to filter
            directory: Optional directory path to filter by. If None, returns all
                igroups.

        Returns:
            List of input groups where all files are within the specified directory.
        """
        if directory is None:
            return igroups

        return [
            igroup
            for igroup in igroups
            if igroup and all(file.is_relative_to(directory) for file in igroup)
        ]

    def _filter_incomplete_igroups(
        self, igroups: List[InputGroup], dataset_dir: Path, output_dir: Path
    ) -> List[InputGroup]:
        """Filter input groups to only include those with incomplete output groups.

        Args:
            igroups: List of input groups to filter
            dataset_dir: Root directory of the dataset
            output_dir: Directory containing outputs

        Returns:
            List of input groups where output groups are not complete.
        """
        incomplete_igroups = []

        for igroup in igroups:
            pogroup = self._effort_model.pogroup_from_igroup(
                dataset_dir, output_dir, igroup
            )
            ogroup = self._effort_model.ogroup_from_pogroup(
                dataset_dir, output_dir, pogroup, igroup
            )

            if not ogroup or not all(output_file.exists() for output_file in ogroup):
                incomplete_igroups.append(igroup)

        return incomplete_igroups

    def _cleanup_incomplete_outputs(
        self, igroups: list[InputGroup], dataset_dir: Path, output_dir: Path
    ) -> None:
        """Clean up incomplete pass outputs and outputs for the given input groups.

        Args:
            igroups: List of input groups to clean up
            dataset_dir: Root directory of the dataset
            output_dir: Directory containing outputs
        """
        for igroup in igroups:
            pogroup = self._effort_model.pogroup_from_igroup(
                dataset_dir, output_dir, igroup
            )
            ogroup = self._effort_model.ogroup_from_pogroup(
                dataset_dir, output_dir, pogroup, igroup
            )

            for po_file in pogroup:
                po_file.unlink(missing_ok=True)

            for o_file in ogroup:
                o_file.unlink(missing_ok=True)

    def _create_metannots(self, run_task: RunTask) -> None:
        dataset_dir = get_dataset_dir(
            self.config.dataset_dir, run_task.dataset_uid_label
        )
        final_output_dir = get_final_output_dir(dataset_dir, run_task.task_id)

        self._metannots_factory.create_metannots(final_output_dir, run_task)
        self._logger.info(f"Created metannots.yml in {final_output_dir}")

    def _run_on_igroup(
        self, dataset_dir: Path, output_dir: Path, igroup: InputGroup
    ) -> None:
        """Run model and postprocess a single input group, then report progress."""
        self.run_model(dataset_dir, output_dir, igroup)

        pogroup = self._effort_model.pogroup_from_igroup(
            dataset_dir, output_dir, igroup
        )

        missing = [f for f in pogroup if not f.exists()]
        if missing:
            raise errors.MissingModelOutputs(missing)

        self.postprocess(dataset_dir, output_dir, pogroup, igroup)
        self._report_progress(dataset_dir)

    def _report_progress(self, dataset_dir: Path) -> None:
        task_id = self._task_id

        if task_id is None:
            return

        progress_info: ProgressInfo
        try:
            progress_info = self._effort_model.get_progress(
                dataset_dir, task_id, self._model_output_folder
            )
        except Exception:
            self._logger.exception(
                f"Failed to calculate progress for task {task_id!s} on dataset \
{dataset_dir}"
            )
            return

        self._logger.info(
            f"Progress: "
            f"{progress_info['completed_passes']}/{progress_info['total_passes']} "
            f"passes complete ({progress_info['completed_progress']:.1%})"
        )
        try:
            self._pubsub.publish(
                channel_name=ChannelName.UPDATE_STATUS,
                cmd=ReportProgress.from_dict(
                    {"task_id": str(task_id), **progress_info}
                ),
            )
        except Exception:
            self._logger.exception("Failed to publish progress.")

    def _wait_for_message(self) -> dict:
        """Block until a message is dequeued and return it."""
        command: dict | None = None

        while (command := self._queue.dequeue()) is None:
            sleep(self._QUEUE_POLL_FREQ_S)

        return command

    def _move_files(self, run_task: RunTask) -> None:
        """Copy model_output_folder contents to the final output directory."""
        if self.model_output_folder is None:
            return

        dataset_dir = get_dataset_dir(
            self.config.dataset_dir, run_task.dataset_uid_label
        )
        final_output_dir: Path = get_final_output_dir(dataset_dir, run_task.task_id)
        final_output_dir.parent.mkdir(parents=True, exist_ok=True)

        shutil.copytree(self.model_output_folder, final_output_dir, dirs_exist_ok=True)

    def _get_output_dir(self, run_task: RunTask) -> Path:
        """Return model_output_folder if set, otherwise the task's final output dir."""
        if self.model_output_folder is not None:
            return self.model_output_folder

        dataset_dir = get_dataset_dir(
            self.config.dataset_dir, run_task.dataset_uid_label
        )
        return get_final_output_dir(dataset_dir, run_task.task_id)

    @property
    def config(self) -> Config:
        """Get the config during the lifecycle of this task."""
        return self._config

    @property
    def model_output_folder(self) -> Path | None:
        """Scratchpad dir for model outputs; if None, no intermediate output dir."""
        return self._model_output_folder

    @model_output_folder.setter
    def model_output_folder(self, value: Path) -> None:
        self._model_output_folder = value

    @abstractmethod
    def run_model(
        self, dataset_dir: Path, output_dir: Path, igroup: InputGroup
    ) -> None:
        """Execute the model on an input group and write pass outputs to `output_dir`.

        Args:
            dataset_dir (Path): Root directory of the dataset, useful for resolving
                paths relative to the dataset structure.
            output_dir (Path): Directory to write pass outputs (pogroup) to.
            igroup (InputGroup): The input files to process in this forward pass.

        Raises:
            Exception: If the model run fails for any reason.
        """
        raise NotImplementedError

    @abstractmethod
    def postprocess(
        self,
        dataset_dir: Path,
        output_dir: Path,
        pogroup: PassOutputGroup,
        igroup: InputGroup,
    ) -> None:
        """Transform pass outputs into final outputs for a single input group.

        Called after `run_model` for each igroup. Use this to move, rename, filter,
        or reformat the raw pass outputs written by `run_model`.

        Args:
            dataset_dir (Path): Root directory of the dataset.
            output_dir (Path): Directory containing the pass outputs written by
                `run_model`.
            pogroup (PassOutputGroup): The pass output files produced by `run_model`
                for this igroup.
            igroup (InputGroup): input group that generated the pogroup.
        """
        raise NotImplementedError
