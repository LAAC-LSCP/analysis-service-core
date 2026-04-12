from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, TypeAlias, TypedDict
from uuid import UUID

from analysis_service_core.src.filesystem import get_final_output_dir

InputGroup: TypeAlias = List[Path]
OutputGroup: TypeAlias = List[Path]


class ForwardPass(TypedDict):
    """
    Represents a single forward pass, including its input group, output group,
    and associated "effort".
    """

    input_group: InputGroup
    output_group: OutputGroup
    effort: float


class EffortModel(ABC):
    """
    Abstract base class representing a collection (batch) of forward passes for a model
    and associated quantities.

    The effort model lets you easily define notions of cost and progress for a given
    model on a dataset.

    Subclasses should implement methods to define how input groups are found, how
    output groups are derived, and how effort is calculated for each input group.
    """

    @abstractmethod
    def find_input_groups(self, dataset_dir: Path) -> List[InputGroup]:
        """
        Find all input groups for the given dataset directory.

        Notes
        -----
        When globbing there is no need to consider what happens with the output folder
        as inputs found in the output folder are automatically "removed" after the fact
        """
        raise NotImplementedError

    @abstractmethod
    def ogroup_from_igroup(
        self, dataset_dir: Path, input_group: InputGroup, output_dir: Path
    ) -> OutputGroup:
        """
        Given an input group and output directory,
        return the corresponding output group.
        """
        raise NotImplementedError

    @abstractmethod
    def effort_from_igroup(self, igroup: InputGroup) -> float:
        """Calculate the effort required for a given input group."""
        raise NotImplementedError

    def _forward_pass_from_igroup(
        self,
        dataset_dir: Path,
        igroup: InputGroup,
        output_dir: Path,
    ) -> ForwardPass:
        """Construct a ForwardPass object from an input group and output directory."""
        return {
            "input_group": igroup,
            "output_group": self.ogroup_from_igroup(
                dataset_dir,
                igroup,
                output_dir=output_dir,
            ),
            "effort": self.effort_from_igroup(igroup),
        }

    def get_progress(
        self,
        dataset_dir: Path,
        task_id: UUID,
        model_output_folder: Optional[Path] = None,
    ) -> float:
        """Calculate the progress so far as a fraction of the total effort."""
        output_dir = model_output_folder or get_final_output_dir(dataset_dir, task_id)

        if not output_dir.exists():
            return 0.0

        igroups = self.find_input_groups(dataset_dir)
        igroups = self._clean_igroups(igroups, output_dir)

        processed_igroups = [
            igroup
            for igroup in igroups
            if all(
                out_file.exists() and out_file.is_file()
                for out_file in self._forward_pass_from_igroup(
                    dataset_dir,
                    igroup,
                    output_dir,
                )["output_group"]
            )
        ]

        effort_so_far = sum(
            self._forward_pass_from_igroup(dataset_dir, igroup, output_dir)["effort"]
            for igroup in processed_igroups
        )
        total_effort = sum(
            self._forward_pass_from_igroup(dataset_dir, igroup, output_dir)["effort"]
            for igroup in igroups
        )

        return effort_so_far / total_effort

    def _clean_igroups(
        self, igroups: List[InputGroup], output_dir: Path
    ) -> List[InputGroup]:
        igroups = [
            [f for f in igroup if not f.is_relative_to(output_dir)]
            for igroup in igroups
        ]
        return [igroup for igroup in igroups if len(igroup)]
