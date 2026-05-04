"""Metannots factory for creating metadata annotation files."""

from abc import ABC, abstractmethod
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Dict

import yaml

from analysis_service_core.src.redis.commands import RunTask


class MetannotsFactory(ABC):
    """Abstract factory for creating metannots.yml files with metadata annotations.

    Subclasses should implement get_default_values() to provide model-specific
    metadata like algorithm name, version, publication details, etc.
    """

    @abstractmethod
    def get_default_values(self) -> Dict[str, Any]:
        """Return default metadata values specific to this model/algorithm.

        Returns:
            Dictionary with default metadata fields e.g., for VTC:
            - segmentation: str
            - segmentation_type: str
            - method: str
            - annotation_algorithm_name: str
            - annotation_algorithm_publication: str
            - annotation_algorithm_version: str
            - annotation_algorithm_repo: str
            - has_speaker_type: str
        """
        raise NotImplementedError

    @abstractmethod
    def get_task_values(self, run_task: RunTask) -> Dict[str, Any]:
        """Extract metadata from the run task."""
        raise NotImplementedError

    def create_metannots(self, final_output_dir: Path, run_task: RunTask) -> None:
        """Create metannots.yml file in the final output directory."""
        metannots_data = self.get_default_values()
        metannots_data.update(self._get_system_values())
        metannots_data.update(self.get_task_values(run_task))

        metannots_file = final_output_dir / "metannots.yml"
        final_output_dir.mkdir(parents=True, exist_ok=True)

        with open(metannots_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(metannots_data, f, default_flow_style=False, sort_keys=False)

    def _get_system_values(self) -> Dict[str, Any]:
        """Get system-generated metadata values like date, package version."""
        system_values = {
            "date_annotation": date.today().strftime("%Y-%m-%d"),
        }

        try:
            system_values["core_package_version"] = version("analysis-service-core")
        except PackageNotFoundError:
            system_values["core_package_version"] = "development"

        return system_values


class DefaultMetannotsFactory(MetannotsFactory):
    """Default implementation providing basic metadata values."""

    def get_default_values(self) -> Dict[str, Any]:
        """Get defaults—mostly unknown."""
        return {
            "method": "automated",
            "annotation_algorithm_name": "unknown",
            "annotation_algorithm_publication": "unknown",
            "annotation_algorithm_version": "unknown",
            "annotation_algorithm_repo": "unknown",
        }

    def get_task_values(self, run_task: RunTask) -> Dict[str, Any]:
        """Get an empty dictionary—no task info."""
        return {}
