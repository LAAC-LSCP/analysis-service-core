from pathlib import Path
from typing import List

from analysis_service_core.src.effort_model import (
    EffortModel,
    InputGroup,
    OutputGroup,
    PassOutputGroup,
)


class WordCountEffortModel(EffortModel):
    def find_igroups(self, dataset_dir: Path) -> List[InputGroup]:
        converted_dir = dataset_dir / "words" / "converted"
        return [[f] for f in converted_dir.rglob("*.txt") if f.is_file()]

    def pogroup_from_igroup(
        self, dataset_dir: Path, output_dir: Path, igroup: InputGroup
    ) -> PassOutputGroup:
        converted_dir = dataset_dir / "words" / "converted"
        pogroup = []
        for f in igroup:
            rel = f.relative_to(converted_dir)
            word_count_file = output_dir / rel
            date_file = word_count_file.with_name("date.txt")
            pogroup.extend([word_count_file, date_file])

        return pogroup

    def ogroup_from_pogroup(
        self, dataset_dir: Path, output_dir: Path, pogroup: PassOutputGroup
    ) -> OutputGroup:
        return [f for f in pogroup if f.name != "date.txt"]

    def effort_ogroup_from_pogroup(
        self, pogroup: PassOutputGroup, ogroup: OutputGroup
    ) -> float:
        return 0.5 * len(ogroup)

    def effort_pogroup_from_igroup(
        self, igroup: InputGroup, pogroup: PassOutputGroup
    ) -> float:
        return sum(self._get_effort_for_file(f) for f in igroup)

    def _get_effort_for_file(self, file: Path) -> float:
        """Calculate effort as the number of lines in a file."""
        with open(file, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
