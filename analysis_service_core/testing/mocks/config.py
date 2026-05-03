"""A mock for Config, avoiding the need to set environment variables."""

from analysis_service_core.src.config import Config, Value


class ConfigMock(Config):
    """A mock Config that skips env var loading entirely."""

    def __init__(self, overrides: dict[str, Value] = {}):
        """Initialise a mock Config."""
        super().__init__(check_required=False)
        for key, value in overrides.items():
            self.set(key, value)
