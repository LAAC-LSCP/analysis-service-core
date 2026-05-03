from pathlib import Path

from analysis_service_core.src.config import Config
from analysis_service_core.testing.mixins.model_integration_test_base import (
    ModelIntegrationTestBase,
)
from analysis_service_core.tests.models.word_count_effort_model import (
    WordCountEffortModel,
)
from analysis_service_core.tests.models.word_count_model import WordCountModel

_NESTED_TEST_DATASET = Path(__file__).parent / "nested_test_datasets"
assert _NESTED_TEST_DATASET.name == "nested_test_datasets"


class TestWordCount(ModelIntegrationTestBase):
    model_mock_cls = WordCountModel
    effort_model_cls = WordCountEffortModel
    queue_name = "RUN_WORD_COUNT_MODEL"  # type: ignore
    config = Config(check_required=False)
    datasets_dir = _NESTED_TEST_DATASET
