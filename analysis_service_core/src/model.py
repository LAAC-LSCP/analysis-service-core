import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from time import sleep
from typing import Optional
from uuid import UUID

from analysis_service_core.src import errors
from analysis_service_core.src.config import Config
from analysis_service_core.src.effort_model import EffortModel, ProgressInfo
from analysis_service_core.src.filesystem import get_dataset_dir, get_final_output_dir
from analysis_service_core.src.logger import LoggerFactory
from analysis_service_core.src.redis.commands import (
    CompleteTask,
    ReportProgress,
    RunTask,
)
from analysis_service_core.src.redis.pubsub import ChannelName, PubSub
from analysis_service_core.src.redis.queue import Queue, QueueName

logger = LoggerFactory.get_logger(__name__)


class ModelPlugin(ABC):
    """
    Abstract base class for machine learning model plugins in the analysis service.

    This class defines the interface and common logic for running models, handling
    input/output directories,
    processing tasks from a queue, and publishing results. Subclasses must implement
    the `run_model` method to define model-specific execution logic.

    Features:
        - Polls a queue for incoming tasks and processes them.
        - Handles dataset and output directory management.
        - Publishes completion messages to a completion queue.
        - Provides hooks for file movement and output folder management.
        - Uses a preconfigured logger for status and error reporting.

    Subclasses should implement:
        - `run_model(dataset_dir: Path, output_dir: Path)`: The core model execution
            logic.

    Example:
        class MyModel(ModelPlugin):
            def run_model(self, dataset_dir: Path, output_dir: Path) -> None:
                # Model-specific logic here
                pass
    """

    _QUEUE_POLL_FREQ_S: int = 1
    _queue: Queue
    _completion_queue: Queue
    _progress_queue: Queue
    _pubsub: PubSub
    _config: Config
    _skip_moving_files: bool
    _model_output_folder: Path | None = None
    _effort_model: EffortModel | None

    def __init__(
        self,
        queue: Queue,
        config: Config,
        pubsub: Optional[PubSub] = None,
        effort_model: Optional[EffortModel] = None,
        skip_moving_files: bool = False,
    ):
        """
        Initialize the model plugin with the given queue, configuration, and options.

        Args:
            queue (Queue): The queue from which to receive tasks for this model.
            config (Config): The configuration object with environment settings.
            skip_moving_files (bool, optional): If True, disables moving output files
                after model run. Defaults to False.

        Raises:
            ValueError: If `skip_moving_files` is False and `model_output_folder` is
                not set.
        """
        self._validate(skip_moving_files)
        self._reset_output_folder()

        logger.info("Starting model...")
        self._queue = queue
        self._completion_queue = Queue(QueueName.COMPLETE_TASK)
        self._progress_queue = Queue(QueueName.PROGRESS)
        self._pubsub = pubsub or PubSub(subscribe_to=[])
        self._config = config
        self._skip_moving_files = skip_moving_files
        self._effort_model = effort_model

    def _validate(self, skip_moving_files: bool) -> None:
        if not skip_moving_files and self.model_output_folder is None:
            raise ValueError("If `skip_moving_files == False`, \
`self.model_output_folder` must be set")

    def _reset_output_folder(self) -> None:
        if self.model_output_folder is not None:
            shutil.rmtree(self.model_output_folder)
            self.model_output_folder.mkdir(parents=True)

    # For the time being do this awkward passing-in of the task id
    # as we make progress reporting optional. Later refactor
    # to make progress reports a natural of the task lifecycle
    def report_progress(self, dataset_dir: Path, task_id: UUID) -> ProgressInfo | None:
        if self._effort_model is None:
            logger.warning("Can't report progress without effort model")

            return None

        progress_info: ProgressInfo
        try:
            progress_info = self._effort_model.get_progress(
                dataset_dir, task_id, self._model_output_folder
            )
        except Exception:
            logger.exception("Problem calculating progress")

            return None

        logger.info("Reporting progress...")
        try:
            self._pubsub.publish(
                channel_name=ChannelName.UPDATE_STATUS,
                cmd=ReportProgress.from_dict(
                    {"task_id": str(task_id), **progress_info}
                ),
            )
        except Exception:
            logger.exception("Problem reporting progress")

            return None

        return progress_info

    def run(self) -> None:
        command: dict = self._wait_for_message()

        run_task = RunTask.from_dict(dict_repr=command)

        dataset_dir = get_dataset_dir(
            self.config.dataset_dir, run_task.dataset_uid_label
        )
        output_dir = self._get_output_dir(run_task)
        task_id = run_task.task_id

        if not dataset_dir.exists():
            logger.error(
                f"Dataset at '{str(dataset_dir)}' not found. Cannot run model."
            )

            return

        try:
            self.run_model(dataset_dir, output_dir, task_id)
        except Exception as e:
            logger.exception(f"Problem running model for task {str(command)}")

            raise errors.RunModelFailed() from e

        if not self._skip_moving_files:
            self._move_files(run_task)

        logger.info("Model ran successfully. Publishing to broker...")
        self._completion_queue.enqueue(CompleteTask(task_id=run_task.task_id))

    def _wait_for_message(self) -> dict:
        command: dict | None = None

        while command is None:
            command = self._queue.dequeue()

            sleep(self._QUEUE_POLL_FREQ_S)

        return command

    def _move_files(self, run_task: RunTask) -> None:
        if self.model_output_folder is None:
            return

        dataset_dir = get_dataset_dir(
            self.config.dataset_dir, run_task.dataset_uid_label
        )
        final_output_dir: Path = get_final_output_dir(dataset_dir, run_task.task_id)
        final_output_dir.parent.mkdir(parents=True, exist_ok=True)

        shutil.copytree(self.model_output_folder, final_output_dir, dirs_exist_ok=True)

    def _get_output_dir(self, run_task: RunTask) -> Path:
        if self.model_output_folder is not None:
            return self.model_output_folder

        dataset_dir = get_dataset_dir(
            self.config.dataset_dir, run_task.dataset_uid_label
        )
        return get_final_output_dir(dataset_dir, run_task.task_id)

    @property
    def config(self) -> Config:
        return self._config

    @property
    def model_output_folder(self) -> Path | None:
        """
        The working directory for model output files.

        If set, this directory is used for intermediate or
        final model outputs.
        If None, the output directory is determined per task.
        """
        return self._model_output_folder

    @model_output_folder.setter
    def model_output_folder(self, value: Path) -> None:
        self._model_output_folder = value

    @abstractmethod
    def run_model(self, dataset_dir: Path, output_dir: Path, task_id: UUID) -> None:
        """
        Run the model on the given dataset and write outputs to the specified directory.

        Args:
            dataset_dir (Path): Path to the input dataset directory.
            output_dir (Path): Path to the output directory for model results.

        Raises:
            Exception: If the model run fails for any reason.
        """
        raise NotImplementedError
