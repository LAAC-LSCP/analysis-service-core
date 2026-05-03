from datetime import datetime, timezone
from pathlib import Path

from analysis_service_core.src.effort_model import InputGroup, PassOutputGroup
from analysis_service_core.src.logger import LoggerFactory
from analysis_service_core.src.model import ModelPlugin

logger = LoggerFactory.get_logger(__name__)


class WordCountModel(ModelPlugin):
    """
    A dummy model that takes a .txt file and gives the word count
    """

    def run_model(
        self, dataset_dir: Path, output_dir: Path, igroup: InputGroup
    ) -> None:
        converted_dir = dataset_dir / "words" / "converted"

        for txt_file in igroup:
            word_count = self._get_word_count(txt_file)
            rel_path = txt_file.relative_to(converted_dir)

            output_file = output_dir / rel_path
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w") as f:
                f.write(f"Word count: {word_count}\n")

            date_file = output_file.with_name("date.txt")
            with open(date_file, "w") as f:
                f.write(datetime.now(timezone.utc).isoformat() + "\n")

    def postprocess(
        self, dataset_dir: Path, output_dir: Path, pogroup: PassOutputGroup
    ) -> None:
        for file in pogroup:
            if file.name == "date.txt":
                file.unlink(missing_ok=True)

    def _get_word_count(self, file: Path) -> int:
        try:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
                words = content.split()
                return len(words)
        except Exception:
            logger.exception(f"Error reading file {file}")
            return 0
