"""Base test class for model integration testing."""

import shutil
from pathlib import Path
from typing import Set, Type
from uuid import UUID

import pytest

from analysis_service_core.src.config import Config
from analysis_service_core.src.effort_model import EffortModel
from analysis_service_core.src.filesystem import get_final_output_dir
from analysis_service_core.src.model import ModelPlugin
from analysis_service_core.src.redis.queue import Queue, QueueName
from analysis_service_core.testing.mocks.pubsub import PubSubMock
from analysis_service_core.testing.mocks.queue import QueueMock

_TASK_ID = UUID("00000000-0000-0000-0000-000000000001")


class ModelIntegrationTestBase:
    """Base class for model integration tests using temporary directories and mocks.

    Test datasets must contain three stage snapshot directories:
      - stage_0/: initial dataset state (inputs only)
      - stage_1/: full dataset state after run_model (inputs + pass outputs)
      - stage_2/: full dataset state after postprocess (inputs + final outputs)

    Model outputs live under outputs/{task_id}/ inside each snapshot,
    mirroring the production layout produced by get_final_output_dir.
    """

    model_cls: Type[ModelPlugin]
    effort_model_cls: Type[EffortModel]

    queue_name: QueueName
    config: Config

    model: ModelPlugin
    effort_model: EffortModel

    datasets_dir: Path

    temp_dataset: Path

    def make_config(self, temp_dataset: Path) -> Config:
        """Return the config for a given temp dataset. Override to add temp paths."""
        return self.config

    def prepare_temp_dataset(self, temp_dataset: Path) -> None:
        """Set up any directories/files needed before model runs. Override as needed."""
        pass

    @pytest.fixture(autouse=True)
    def setup_temp_dirs(self, tmp_path):
        """Copy stage_0 into a temp directory and initialize model and effort model."""
        self.temp_dataset = tmp_path / "dataset"
        shutil.copytree(self.stage_0, self.temp_dataset)
        self.prepare_temp_dataset(self.temp_dataset)

        config = self.make_config(self.temp_dataset)
        self.effort_model = self.effort_model_cls(config=config)

        self.model = self.model_cls(
            queue=QueueMock(name=self.queue_name),
            config=config,
            effort_model=self.effort_model,
            pubsub=PubSubMock(),
            model_output_folder=None,
            _completion_queue=QueueMock(name=QueueName.COMPLETE_TASK),
            _progress_queue=QueueMock(name=QueueName.PROGRESS),
        )

    def _run_pipeline(self) -> None:
        """Run the pipeline igroup-by-igroup, matching model.py's execution order.

        For each igroup: run_model → assert pogroup exists → postprocess → assert ogroup
        exists. Asserts inline so failures are attributed to the specific igroup and
        stage.
        """
        for igroup in self.effort_model.find_sorted_igroups(self.temp_dataset):
            self.model.run_model(self.temp_dataset, self.temp_output_dir, igroup)
            pogroup = self.effort_model.pogroup_from_igroup(
                self.temp_dataset, self.temp_output_dir, igroup
            )
            for f in pogroup:
                assert f.exists(), f"Expected pass output missing: {f}"

            self.model.postprocess(
                self.temp_dataset, self.temp_output_dir, pogroup, igroup
            )
            ogroup = self.effort_model.ogroup_from_pogroup(
                self.temp_dataset, self.temp_output_dir, pogroup, igroup
            )
            for f in ogroup:
                assert f.exists(), f"Expected output missing: {f}"

    def test_setup_correct(self) -> None:
        """Stage snapshot directories all exist."""
        assert self.stage_0.exists()
        assert self.stage_1.exists()
        assert self.stage_2.exists()

    def test_igroup_pipeline(self) -> None:
        """Each igroup produces its expected pass output and final output files."""
        self._run_pipeline()

    def test_full_pass_output_matches(self) -> None:
        """Full dataset state after run_model matches the stage_1 reference snapshot."""
        for igroup in self.effort_model.find_sorted_igroups(self.temp_dataset):
            self.model.run_model(self.temp_dataset, self.temp_output_dir, igroup)

        actual: Set[Path] = {
            f.relative_to(self.temp_dataset)
            for f in self.temp_dataset.rglob("**")
            if f.is_file()
        }
        expected: Set[Path] = {
            f.relative_to(self.stage_1) for f in self.stage_1.rglob("**") if f.is_file()
        }
        assert actual == expected

    def test_full_output_matches(self) -> None:
        """Full dataset state after the pipeline matches the stage_2 snapshot."""
        self._run_pipeline()

        actual: Set[Path] = {
            f.relative_to(self.temp_dataset)
            for f in self.temp_dataset.rglob("**")
            if f.is_file()
        }
        expected: Set[Path] = {
            f.relative_to(self.stage_2) for f in self.stage_2.rglob("**") if f.is_file()
        }
        assert actual == expected

    @property
    def stage_0(self) -> Path:
        """Initial dataset state (inputs only)."""
        return self.datasets_dir / "stage_0"

    @property
    def stage_1(self) -> Path:
        """Dataset state after run_model."""
        return self.datasets_dir / "stage_1"

    @property
    def stage_2(self) -> Path:
        """Dataset state after postprocess."""
        return self.datasets_dir / "stage_2"

    @property
    def temp_output_dir(self) -> Path:
        """Output directory within the temporary dataset, matching production layout."""
        return get_final_output_dir(self.temp_dataset, _TASK_ID)

    @property
    def queue(self) -> Queue:
        """Return the model's task queue."""
        return self.model._queue

    @property
    def completion_queue(self) -> Queue:
        """Return the model's completion queue."""
        return self.model._completion_queue

    @property
    def progress_queue(self):
        """Return the model's progress queue."""
        return self.model._progress_queue
