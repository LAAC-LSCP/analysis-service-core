"""Base test class for effort model integration testing."""

import json
from pathlib import Path
from typing import Dict, List, Type, TypedDict

from analysis_service_core.src.effort_model import EffortModel


class _ForwardPassExpectation(TypedDict):
    igroup: List[str]
    pogroup: List[str]
    ogroup: List[str]
    pass_effort: float
    output_effort: float


_ExpectedByIgroup = Dict[frozenset[Path], _ForwardPassExpectation]


class EffortModelTestBase:
    """Base class for effort model tests against a reference dataset.

    Validates that an EffortModel correctly maps igroups to pogroups and ogroups,
    and that computed efforts match a JSON file of expected values.

    No temporary directories are used — all checks run against the reference dataset.

    Example:
        class TestWordCountEffortModel(EffortModelTestBase):
            effort_model_cls = WordCountEffortModel
            datasets_dir = Path(__file__).parent / "nested_test_datasets"
            expected_forward_passes_json =
                Path(__file__).parent / "expected_forward_passes.json"
    """

    effort_model_cls: Type[EffortModel]
    datasets_dir: Path
    expected_forward_passes_json: Path

    effort_model: EffortModel

    def setup_method(self):
        """Instantiate the effort model before each test."""
        self.effort_model = self.effort_model_cls()

    def _load_expected(self) -> _ExpectedByIgroup:
        with open(self.expected_forward_passes_json) as f:
            entries: List[_ForwardPassExpectation] = json.load(f)

        return {frozenset(Path(p) for p in entry["igroup"]): entry for entry in entries}

    def _igroup_key(self, igroup) -> frozenset:
        return frozenset(f.relative_to(self.inputs) for f in igroup)

    def test_igroups_found(self) -> None:
        """Igroups found match the expected igroups declared in the JSON."""
        actual = {
            self._igroup_key(igroup)
            for igroup in self.effort_model.find_sorted_igroups(self.inputs)
        }

        assert actual == set(self._load_expected().keys())

    def test_pogroup_mapping(self) -> None:
        """Each igroup maps to exactly the pogroup declared in the JSON."""
        expected = self._load_expected()
        for igroup in self.effort_model.find_sorted_igroups(self.inputs):
            entry = expected[self._igroup_key(igroup)]
            pogroup = self.effort_model.pogroup_from_igroup(
                self.inputs, self.pass_outputs, igroup
            )
            actual = frozenset(f.relative_to(self.pass_outputs) for f in pogroup)

            assert actual == frozenset(Path(p) for p in entry["pogroup"])

    def test_ogroup_mapping(self) -> None:
        """Each pogroup maps to exactly the ogroup declared in the JSON."""
        expected = self._load_expected()
        for igroup in self.effort_model.find_sorted_igroups(self.inputs):
            entry = expected[self._igroup_key(igroup)]
            pogroup = self.effort_model.pogroup_from_igroup(
                self.inputs, self.pass_outputs, igroup
            )
            ogroup = self.effort_model.ogroup_from_pogroup(
                self.inputs, self.pass_outputs, pogroup, igroup
            )
            actual = frozenset(f.relative_to(self.pass_outputs) for f in ogroup)

            assert actual == frozenset(Path(p) for p in entry["ogroup"])

    def test_effort(self) -> None:
        """Both pass and output effort match expected values for each forward pass."""
        expected = self._load_expected()
        for igroup in self.effort_model.find_sorted_igroups(self.inputs):
            entry = expected[self._igroup_key(igroup)]
            pogroup = self.effort_model.pogroup_from_igroup(
                self.inputs, self.pass_outputs, igroup
            )
            ogroup = self.effort_model.ogroup_from_pogroup(
                self.inputs, self.pass_outputs, pogroup, igroup
            )

            pass_effort = self.effort_model.effort_pogroup_from_igroup(igroup, pogroup)

            assert pass_effort == entry["pass_effort"], (
                f"Pass effort mismatch for igroup {igroup}: "
                f"got {pass_effort}, expected {entry['pass_effort']}"
            )

            output_effort = self.effort_model.effort_ogroup_from_pogroup(
                pogroup, ogroup, igroup
            )

            assert output_effort == entry["output_effort"], (
                f"Output effort mismatch for igroup {igroup}: "
                f"got {output_effort}, expected {entry['output_effort']}"
            )

    @property
    def inputs(self) -> Path:
        """Return path to reference input directory."""
        return self.datasets_dir / "inputs"

    @property
    def pass_outputs(self) -> Path:
        """Return path to reference pass outputs directory."""
        return self.datasets_dir / "pass_outputs"

    @property
    def outputs(self) -> Path:
        """Return path to reference outputs directory."""
        return self.datasets_dir / "outputs"
