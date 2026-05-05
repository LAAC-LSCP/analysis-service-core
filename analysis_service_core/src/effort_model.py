"""Effort model abstraction for tracking task progress and cost for forward passes."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, TypeAlias, TypedDict
from uuid import UUID

from analysis_service_core.src.config import Config
from analysis_service_core.src.filesystem import get_final_output_dir

InputGroup: TypeAlias = List[Path]
# Intermediate outputs of input groups—outputs of subprocess calls
PassOutputGroup: TypeAlias = List[Path]
# Final outputs, after post-processing pass output groups in the output folder
OutputGroup: TypeAlias = List[Path]


class ProgressInfo(TypedDict):
    """Snapshot of task progress metrics at a given point in time."""

    completed_progress: float
    completed_pass_effort: float
    partial_pass_progress: float
    partial_pass_effort: float
    total_effort: float
    completed_passes: int
    total_passes: int


class ForwardPass(TypedDict):
    """A single forward pass with its input/output groups and effort cost."""

    input_group: InputGroup
    pass_output_group: PassOutputGroup
    output_group: OutputGroup
    effort: float


class EffortModel(ABC):
    """ABC for defining cost and progress tracking for a model on a dataset.

    Subclasses implement how input groups are found, how output groups are derived, and
    how effort is calculated per input group.
    """

    config: Config

    def __init__(self, config: Config):
        """Initialise the effort model."""
        self.config = config

    @abstractmethod
    def find_igroups(self, dataset_dir: Path) -> List[InputGroup]:
        """Find all input groups in the dataset directory.

        Inputs found inside the output folder are automatically excluded.
        """
        raise NotImplementedError

    @abstractmethod
    def pogroup_from_igroup(
        self, dataset_dir: Path, output_dir: Path, igroup: InputGroup
    ) -> PassOutputGroup:
        """Return the pass output group for an input group."""
        raise NotImplementedError

    @abstractmethod
    def ogroup_from_pogroup(
        self,
        dataset_dir: Path,
        output_dir: Path,
        pogroup: PassOutputGroup,
        igroup: InputGroup,
    ) -> OutputGroup:
        """Return the final output group derived from a pass output group."""
        raise NotImplementedError

    @abstractmethod
    def effort_pogroup_from_igroup(
        self, igroup: InputGroup, pogroup: PassOutputGroup
    ) -> float:
        """Return the effort of processing an input group into a pass output group."""
        raise NotImplementedError

    def find_sorted_igroups(self, dataset_dir: Path) -> List[InputGroup]:
        """Return input groups with files sorted in each group, sorted by path."""
        return sorted([sorted(igroup) for igroup in self.find_igroups(dataset_dir)])

    def effort_ogroup_from_pogroup(
        self,
        pogroup: PassOutputGroup,
        ogroup: OutputGroup,
        igroup: InputGroup,
    ) -> float:
        """Return the effort of post-processing a pass output group. Defaults to 0."""
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
                igroup,
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
        ogroup = self.ogroup_from_pogroup(dataset_dir, output_dir, pogroup, igroup)
        effort = self.effort_pogroup_from_igroup(
            igroup, pogroup
        ) + self.effort_ogroup_from_pogroup(pogroup, ogroup, igroup)

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
