"""Base test class for model integration testing."""

import shutil
from pathlib import Path
from typing import Set, Type

import pytest

from analysis_service_core.src.config import Config
from analysis_service_core.src.effort_model import EffortModel
from analysis_service_core.src.model import ModelPlugin
from analysis_service_core.src.redis.queue import Queue, QueueName
from analysis_service_core.testing.mocks.pubsub import PubSubMock
from analysis_service_core.testing.mocks.queue import QueueMock


class ModelIntegrationTestBase:
    """Base class for model integration tests using temporary directories and mocks."""

    model_mock_cls: Type[ModelPlugin]
    effort_model_cls: Type[EffortModel]

    queue_name: QueueName
    config: Config

    model_mock: ModelPlugin
    effort_model_mock: EffortModel

    datasets_dir: Path

    _temp_datasets_dir: Path

    @pytest.fixture(autouse=True)
    def setup_temp_dirs(self, tmp_path):
        """Set up temporary test directories and initialize model mock."""
        test_data_dir = tmp_path / "test_datasets"
        self._temp_datasets_dir = test_data_dir

        shutil.copytree(self.datasets_dir, test_data_dir)

        self.effort_model_mock = self.effort_model_cls()

        self.model_mock = self.model_mock_cls(
            queue=QueueMock(name=self.queue_name),
            config=self.config,
            effort_model=self.effort_model_mock,
            pubsub=PubSubMock(),
            model_output_folder=None,
            _completion_queue=QueueMock(name=QueueName.COMPLETE_TASK),
            _progress_queue=QueueMock(name=QueueName.PROGRESS),
        )

    def test_setup_correct(self) -> None:
        """Test that source dataset directories exist."""
        assert (self.datasets_dir / "inputs").exists()
        assert (self.datasets_dir / "pass_outputs").exists()
        assert (self.datasets_dir / "outputs").exists()

    def test_run_model_expected_files(self) -> None:
        """Test model run produces expected pass output and final output files."""
        input_igroups = self.effort_model_mock.find_igroups(self.temp_inputs)

        for igroup in input_igroups:
            self.model_mock.run_model(
                dataset_dir=self.temp_inputs,
                output_dir=self.temp_pass_outputs,
                igroup=igroup,
            )

        pofiles: Set[Path] = {
            f.relative_to(self.temp_pass_outputs)
            for f in self.temp_pass_outputs.rglob("**")
            if f.is_file()
        }
        expected_pofiles: Set[Path] = {
            f.relative_to(self.pass_outputs)
            for f in self.pass_outputs.rglob("**")
            if f.is_file()
        }

        assert pofiles == expected_pofiles

        for pogroup in [
            self.effort_model_mock.pogroup_from_igroup(
                self.temp_inputs, self.temp_pass_outputs, igroup
            )
            for igroup in input_igroups
        ]:
            self.model_mock.postprocess(self.temp_inputs, self.temp_outputs, pogroup)

        ofiles: Set[Path] = {
            f.relative_to(self.temp_outputs)
            for f in self.temp_outputs.rglob("**")
            if f.is_file()
        }
        expected_ofiles: Set[Path] = {
            f.relative_to(self.outputs) for f in self.outputs.rglob("**") if f.is_file()
        }

        assert ofiles == expected_ofiles

    @property
    def inputs(self) -> Path:
        """Return path to original input directory."""
        return self.datasets_dir / "inputs"

    @property
    def pass_outputs(self) -> Path:
        """Return path to original pass outputs directory."""
        return self.datasets_dir / "pass_outputs"

    @property
    def outputs(self) -> Path:
        """Return path to original outputs directory."""
        return self.datasets_dir / "outputs"

    @property
    def temp_inputs(self) -> Path:
        """Return path to temporary input directory."""
        return self._temp_datasets_dir / "inputs"

    @property
    def temp_pass_outputs(self) -> Path:
        """Return path to temporary pass outputs directory."""
        return self._temp_datasets_dir / "pass_outputs"

    @property
    def temp_outputs(self) -> Path:
        """Return path to temporary outputs directory."""
        return self._temp_datasets_dir / "outputs"

    @property
    def queue(self) -> Queue:
        """Return the main queue mock."""
        return self.model_mock._queue

    @property
    def completion_queue(self) -> Queue:
        """Return the completion queue mock."""
        return self.model_mock._completion_queue

    @property
    def progress_queue(self):
        """Return the progress queue mock."""
        return self.model_mock._progress_queue
