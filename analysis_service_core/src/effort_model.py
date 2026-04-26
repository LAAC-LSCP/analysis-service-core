from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, TypeAlias, TypedDict
from uuid import UUID

from analysis_service_core.src.filesystem import get_final_output_dir

InputGroup: TypeAlias = List[Path]
PassOutputGroup: TypeAlias = List[Path]
OutputGroup: TypeAlias = List[Path]


class ProgressInfo(TypedDict):
    completed_progress: float
    completed_pass_effort: float
    partial_pass_progress: float
    partial_pass_effort: float
    total_effort: float
    completed_passes: int
    total_passes: int


class ForwardPass(TypedDict):
    """
    Represents a single forward pass, including its input group, output group,
    and associated "effort".
    """

    input_group: InputGroup
    pass_output_group: PassOutputGroup
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
    def find_igroups(self, dataset_dir: Path) -> List[InputGroup]:
        """
        Find all input groups for the given dataset directory.

        Notes
        -----
        When globbing there is no need to consider what happens with the output folder
        as inputs found in the output folder are automatically "removed" after the fact
        """
        raise NotImplementedError

    @abstractmethod
    def pogroup_from_igroup(
        self, dataset_dir: Path, output_dir: Path, igroup: InputGroup
    ) -> PassOutputGroup:
        """
        Given an input group and output directory, return the corresponding pass output
        group—the immediate outputs of the subprocess call/model run.
        """
        raise NotImplementedError

    @abstractmethod
    def ogroup_from_pogroup(
        self, dataset_dir: Path, output_dir: Path, pogroup: PassOutputGroup
    ) -> OutputGroup:
        """
        Given a pass output group and output directory, return the corresponding output
        group.
        """
        raise NotImplementedError

    @abstractmethod
    def effort_pogroup_from_igroup(
        self, igroup: InputGroup, pogroup: PassOutputGroup
    ) -> float:
        """
        Calculate the effort required for a given input group to construct a given
        output group.
        """
        raise NotImplementedError

    def find_sorted_igroups(self, dataset_dir: Path) -> List[InputGroup]:
        return sorted([sorted(igroup) for igroup in self.find_igroups(dataset_dir)])

    def effort_ogroup_from_pogroup(
        self, pogroup: PassOutputGroup, ogroup: OutputGroup
    ) -> float:
        """
        Calculate the effort required for a given pass output group to be
        post-processed.
        """
        return 0.0

    def get_progress(
        self,
        dataset_dir: Path,
        task_id: UUID,
        model_output_folder: Optional[Path] = None,
    ) -> ProgressInfo:
        """Calculate the progress so far as a fraction of the total effort."""
        output_dir = model_output_folder or get_final_output_dir(dataset_dir, task_id)
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        task_igroups = self.find_igroups(dataset_dir)
        task_igroups = self._filter_igroups(task_igroups, output_dir)

        forward_passes = [
            (igroup, self._forward_pass_from_igroup(dataset_dir, output_dir, igroup))
            for igroup in task_igroups
        ]

        task_effort = sum(fp["effort"] for _, fp in forward_passes)

        complete_pass_effort = sum(
            fp["effort"]
            for _, fp in forward_passes
            if all(f.exists() and f.is_file() for f in fp["output_group"])
        )

        partial_pass_effort = sum(
            self.effort_pogroup_from_igroup(
                igroup,
                [f for f in fp["pass_output_group"] if f.exists() and f.is_file()],
            )
            + self.effort_ogroup_from_pogroup(
                fp["pass_output_group"],
                [f for f in fp["output_group"] if f.exists() and f.is_file()],
            )
            for igroup, fp in forward_passes
            if any(f.exists() and f.is_file() for f in fp["pass_output_group"])
        )

        return {
            "completed_progress": (
                complete_pass_effort / task_effort if task_effort else 0.0
            ),
            "completed_pass_effort": complete_pass_effort,
            "partial_pass_progress": (
                partial_pass_effort / task_effort if task_effort else 0.0
            ),
            "partial_pass_effort": partial_pass_effort,
            "total_effort": task_effort,
            "completed_passes": sum(
                1
                for _, fp in forward_passes
                if all(f.exists() and f.is_file() for f in fp["output_group"])
            ),
            "total_passes": len(task_igroups),
        }

    def _forward_pass_from_igroup(
        self,
        dataset_dir: Path,
        output_dir: Path,
        igroup: InputGroup,
    ) -> ForwardPass:
        """Construct a ForwardPass object from an input group and output directory."""
        pogroup = self.pogroup_from_igroup(dataset_dir, output_dir, igroup)
        ogroup = self.ogroup_from_pogroup(dataset_dir, output_dir, pogroup)
        effort = self.effort_pogroup_from_igroup(
            igroup, pogroup
        ) + self.effort_ogroup_from_pogroup(pogroup, ogroup)

        return {
            "input_group": igroup,
            "pass_output_group": pogroup,
            "output_group": ogroup,
            "effort": effort,
        }

    def _filter_igroups(
        self, igroups: List[InputGroup], output_dir: Path
    ) -> List[InputGroup]:
        igroups = [
            [f for f in igroup if not f.is_relative_to(output_dir)]
            for igroup in igroups
        ]
        return [igroup for igroup in igroups if len(igroup)]
