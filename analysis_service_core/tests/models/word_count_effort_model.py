from pathlib import Path
from typing import List

from analysis_service_core.src.effort_model import EffortModel, InputGroup, OutputGroup


class WordCountEffortModel(EffortModel):
    def find_input_groups(self, dataset_dir: Path) -> List[InputGroup]:
        return [[f] for f in dataset_dir.rglob("**.txt") if f.is_file()]

    def ogroup_from_igroup(
        self, dataset_dir: Path, input_group: InputGroup, output_dir: Path
    ) -> OutputGroup:
        converted_dir = dataset_dir / "words" / "converted"
        igroup_with_rel_paths = [
            file.relative_to(converted_dir) for file in input_group
        ]

        return [output_dir / f for f in igroup_with_rel_paths]

    def effort_from_igroup(self, igroup: InputGroup):
        return sum(self._get_effort_for_file(f) for f in igroup)

    def _get_effort_for_file(self, file: Path) -> float:
        """Calculate effort as the number of lines in a file."""
        with open(file, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
