"""Mixin classes for testing.

This module provides reusable test base classes that use inheritance-based mixins
to share common testing functionality across different model implementations.

The main pattern is to create a base test class that defines:
1. Class attributes for configuration (model class, effort model, directories, etc.)
2. Common setup logic using pytest fixtures
3. Generic test methods that work with any model implementation
4. Utility properties and methods for accessing test resources

Usage Pattern:
    class TestMyModel(ModelIntegrationTestBase):
        # Configure the base class with your specific implementations
        model_mock_cls = MyModelImplementation
        effort_model_cls = MyEffortModelImplementation
        queue_name = QueueName.MY_QUEUE
        config = Config(check_required=False)
        datasets_dir = Path(__file__).parent / "test_datasets"

        # The base class automatically provides:
        # - Temporary directory setup with fresh copies of test data
        # - Model instance creation with mocked dependencies
        # - Common test methods like test_run_model_expected_files()
        # - Access to both original and temporary directory paths

The mixins handle complex setup like temporary directory management, dependency
injection with underscored parameters for advanced configuration, and provide
both generic tests and utilities for writing model-specific tests.
"""

from .effort_model_test_base import EffortModelTestBase
from .model_e2e_test_base import ModelE2ETestBase
from .model_integration_test_base import ModelIntegrationTestBase

__all__ = [
    "EffortModelTestBase",
    "ModelE2ETestBase",
    "ModelIntegrationTestBase",
]
