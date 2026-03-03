import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from time import sleep
from uuid import UUID

from analysis_service_core.src import errors
from analysis_service_core.src.config import Config
from analysis_service_core.src.logger import LoggerFactory
from analysis_service_core.src.redis.commands import CompleteTask, RunTask
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
    _config: Config
    _skip_moving_files: bool
    _model_output_folder: Path | None = None

    def __init__(
        self,
        queue: Queue,
        config: Config,
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
        self._config = config
        self._skip_moving_files = skip_moving_files

    def _validate(self, skip_moving_files: bool) -> None:
        if not skip_moving_files and self.model_output_folder is None:
            raise ValueError(
                "If `skip_moving_files == False`, \
`self.model_output_folder` must be set"
            )

    def _reset_output_folder(self) -> None:
        if self.model_output_folder is not None:
            shutil.rmtree(self.model_output_folder)
            self.model_output_folder.mkdir(parents=True)

    def run(self) -> None:
        command: dict = self._wait_for_message()

        run_task = RunTask.from_dict(dict_repr=command)

        dataset_dir = self._get_dataset_dir(run_task)
        output_dir = self._get_output_dir(run_task)

        if not dataset_dir.exists():
            logger.error(
                f"Dataset at '{str(dataset_dir)}' not found. Cannot run model."
            )

            return

        try:
            self.run_model(dataset_dir, output_dir)
        except Exception as e:
            logger.error(f"Problem running model for task {str(command)}: {str(e)}")

            raise errors.RunModelFailed() from e

        if not self._skip_moving_files:
            self._move_files(run_task)

        logger.info("Model ran successfully. Publishing to redis...")
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

        final_output_dir: Path = self._get_final_output_dir(run_task)
        final_output_dir.parent.mkdir(parents=True, exist_ok=True)

        shutil.copytree(self.model_output_folder, final_output_dir, dirs_exist_ok=True)

    def _get_dataset_dir(self, run_task: RunTask) -> Path:
        # dataset_uid = self._uid_label_to_uid(run_task.dataset_uid_label)
        dataset_uid = run_task.dataset_uid_label

        return self.config.dataset_dir / str(dataset_uid)

    def _get_output_dir(self, run_task: RunTask) -> Path:
        if self.model_output_folder is not None:
            return self.model_output_folder

        return self._get_final_output_dir(run_task)

    def _get_final_output_dir(self, run_task: RunTask) -> Path:
        return self._get_dataset_dir(run_task) / "outputs" / str(run_task.task_id)

    # def _uid_label_to_uid(self, uid_label: str) -> UUID:
    #     return UUID(uid_label.split("_")[-1])

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
    def run_model(self, dataset_dir: Path, output_dir: Path) -> None:
        """
        Run the model on the given dataset and write outputs to the specified directory.

        Args:
            dataset_dir (Path): Path to the input dataset directory.
            output_dir (Path): Path to the output directory for model results.

        Raises:
            Exception: If the model run fails for any reason.
        """
        return NotImplemented
