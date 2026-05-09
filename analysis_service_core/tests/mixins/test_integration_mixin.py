from pathlib import Path

from analysis_service_core.src.config import Config
from analysis_service_core.testing.mixins import (
    ModelIntegrationTestBase,
)
from analysis_service_core.testing.models import WordCountEffortModel, WordCountModel

_NESTED_TEST_DATASET = Path(__file__).parent / "nested_test_datasets"
assert _NESTED_TEST_DATASET.exists()


class TestWordCount(ModelIntegrationTestBase):
    model_cls = WordCountModel
    effort_model_cls = WordCountEffortModel
    queue_name = "RUN_WORD_COUNT_MODEL"  # type: ignore
    config = Config(check_required=False)
    datasets_dir = _NESTED_TEST_DATASET
