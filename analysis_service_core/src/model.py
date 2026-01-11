import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from time import sleep
from uuid import UUID

from analysis_service_core.src.config import Config
from analysis_service_core.src.redis.commands import CompleteTask, RunTask
from analysis_service_core.src.redis.queue import Queue, QueueName


class ModelPlugin(ABC):
    # TODO: Think about how partial failure should be represented
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
        self._validate(skip_moving_files)
        self._reset_output_folder()

        print("Starting model...")
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

        try:
            run_task = RunTask.from_dict(dict_repr=command)
        except Exception as e:
            print(
                f"Could not handle incoming Redis command '{command}': \
{e}... Stopping model."
            )

            return

        dataset_dir = self._get_dataset_dir(run_task)
        output_dir = self._get_output_dir(run_task)

        if not dataset_dir.exists():
            print(f"Dataset at '{str(dataset_dir)}' not found. Cannot run model.")

            return

        try:
            self.run_model(dataset_dir, output_dir)

            if not self._skip_moving_files:
                self._move_files(run_task)

            print("Model ran successfully. Publishing to redis...")
            self._completion_queue.enqueue(CompleteTask(task_id=run_task.task_id))
        except Exception as e:
            print(f"Problem running model for task {str(command)}: {str(e)}")

            return

    def _wait_for_message(self) -> dict:
        command: dict | None = None

        while command is None:
            command = self._queue.dequeue()

            sleep(1)

        return command

    def _move_files(self, run_task: RunTask) -> None:
        if self.model_output_folder is None:
            return

        final_output_dir: Path = self._get_final_output_dir(run_task)
        final_output_dir.parent.mkdir(parents=True, exist_ok=True)

        shutil.copytree(self.model_output_folder, final_output_dir, dirs_exist_ok=True)

    def _get_dataset_dir(self, run_task: RunTask) -> Path:
        dataset_uid = self._uid_label_to_uid(run_task.dataset_uid_label)

        return self.config.dataset_dir / str(dataset_uid)

    def _get_output_dir(self, run_task: RunTask) -> Path:
        if self.model_output_folder is not None:
            return self.model_output_folder

        return self._get_final_output_dir(run_task)

    def _get_final_output_dir(self, run_task: RunTask) -> Path:
        dataset_uid = self._uid_label_to_uid(run_task.dataset_uid_label)

        return (
            self.config.echolalia_outputs_dir / str(dataset_uid) / str(run_task.task_id)
        )

    def _uid_label_to_uid(self, uid_label: str) -> UUID:
        return UUID(uid_label.split("_")[-1])

    @property
    def config(self) -> Config:
        return self._config

    @property
    def model_output_folder(self) -> Path | None:
        return self._model_output_folder

    @model_output_folder.setter
    def model_output_folder(self, value: Path) -> None:
        self._model_output_folder = value

    @abstractmethod
    def run_model(self, dataset_dir: Path, output_dir: Path) -> None:
        return NotImplemented
