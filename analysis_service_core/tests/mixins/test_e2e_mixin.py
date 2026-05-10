from pathlib import Path
from uuid import UUID

from analysis_service_core.src.redis.commands import Operation
from analysis_service_core.src.redis.queue import QueueName
from analysis_service_core.testing.mixins import ModelE2ETestBase
from analysis_service_core.testing.models import WordCountEffortModel

_CORE_ROOT = Path(__file__).parents[3]
_TESTS_DIR = Path(__file__).parents[1]


class TestWordCountE2E(ModelE2ETestBase):
    queue_name = QueueName.RUN_TEST_MODEL
    operation = Operation.RUN_TEST_MODEL
    dockerfile = _TESTS_DIR / "word_count_worker" / "Dockerfile"
    build_context = _CORE_ROOT
    datasets_dir = _TESTS_DIR / "datasets"
    echolalia_dir = _TESTS_DIR / "dummy_echolalia"
    DATASET_UID = UUID("51088a18-6c2a-4e65-ae00-8b62d86fe66e")
    worker_env = {}

    effort_model_cls = WordCountEffortModel
    TEST_IDEMPOTENCY = True
