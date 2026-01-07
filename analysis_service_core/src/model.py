import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

from analysis_service_core.src.config import Config
from analysis_service_core.src.redis.channels import ChannelName
from analysis_service_core.src.redis.commands import CompleteTask, RunTask
from analysis_service_core.src.redis.pubsub import PubSub


class ModelPlugin(ABC):
    # TODO: Think about how partial failure should be represented
    _pubsub: PubSub
    _config: Config
    _skip_moving_files: bool
    _model_output_folder: Path | None = None

    def __init__(
        self,
        pubsub: PubSub,
        config: Config,
        skip_moving_files: bool = False,
    ):
        self._validate(skip_moving_files)
        self._reset_output_folder()

        print("Starting model...")
        self._pubsub = pubsub
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
        for message in self._pubsub.listen():
            try:
                data = self._pubsub.get_data_from_message(message)
                run_task = RunTask.from_dict(dict_repr=data)

            except Exception as e:
                print(f"Could not handle incoming Redis message '{message}': {e}")
                continue

            dataset_dir = self._get_dataset_dir(run_task)
            output_dir = self._get_output_dir(run_task)

            if not (dataset_dir).exists():
                print(
                    f"Dataset '{run_task.dataset_uid_label}' not found in \
'{self._config.get("DATASETS_DIR")}'. Cannot run model."
                )
                continue

            try:
                self.run_model(dataset_dir, output_dir)

                if not self._skip_moving_files:
                    self._move_files(run_task)

                print("Model ran successfully. Publishing to redis...")
                self._pubsub.publish(
                    ChannelName.COMPLETE_TASK, CompleteTask(task_id=run_task.task_id)
                )
            except Exception as e:
                print(f"Problem running model for task {str(message)}: {str(e)}")
                continue

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
