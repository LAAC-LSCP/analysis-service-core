from pathlib import Path
from typing import List, Optional
from uuid import UUID

from analysis_service_core.src.config import Config
from analysis_service_core.src.logger import LoggerFactory
from analysis_service_core.src.model import ModelPlugin
from analysis_service_core.src.redis.pubsub import PubSub
from analysis_service_core.src.redis.queue import Queue, QueueName
from analysis_service_core.testing.mocks.queue import QueueMock
from analysis_service_core.tests.models.word_count_effort_model import (
    WordCountEffortModel,
)

logger = LoggerFactory.get_logger(__name__)


class WordCountModel(ModelPlugin):
    """
    A dummy model that takes a .txt file and gives the word count
    """

    def __init__(
        self,
        queue: Queue,
        config: Config,
        effort_model: WordCountEffortModel,
        pubsub: Optional[PubSub] = None,
        model_output_folder: Optional[Path] = None,
        mock_completion_queue: bool = True,
    ) -> None:
        if model_output_folder:
            self.model_output_folder = model_output_folder

        super().__init__(
            queue=queue,
            config=config,
            pubsub=pubsub,
            effort_model=effort_model,
            skip_moving_files=model_output_folder is None,
        )

        if mock_completion_queue:
            self._completion_queue = QueueMock(QueueName.COMPLETE_TASK)  # type: ignore

    def run_model(self, dataset_dir: Path, output_dir: Path, task_id: UUID) -> None:
        converted_dir = dataset_dir / "words" / "converted"

        if not converted_dir.exists():
            raise FileNotFoundError(f"Directory {converted_dir} does not exist")

        txt_files: List[Path] = list(converted_dir.rglob("*.txt"))

        for txt_file in txt_files:
            word_count = self._get_word_count(txt_file)

            rel_path = txt_file.relative_to(converted_dir)

            output_file = output_dir / rel_path
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w") as f:
                f.write(f"Word count: {word_count}\n")

            self.report_progress(dataset_dir, task_id)

    def _get_word_count(self, file: Path) -> int:
        try:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
                words = content.split()
                return len(words)
        except Exception:
            logger.exception(f"Error reading file {file}")
            return 0
