from pathlib import Path

from analysis_service_core.testing.mixins import (
    EffortModelTestBase,
)
from analysis_service_core.testing.mocks.config import ConfigMock
from analysis_service_core.tests.models.word_count_effort_model import (
    WordCountEffortModel,
)

_NESTED_TEST_DATASET = Path(__file__).parent / "nested_test_datasets"
assert _NESTED_TEST_DATASET.exists()

_FORWARD_PASSES_JSON = Path(__file__).parent / "nested_efforts.json"
assert _FORWARD_PASSES_JSON.exists()


class TestWordCountEffortModel(EffortModelTestBase):
    effort_model_cls = WordCountEffortModel
    datasets_dir = _NESTED_TEST_DATASET
    expected_forward_passes_json = _FORWARD_PASSES_JSON
    config = ConfigMock()
