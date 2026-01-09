from pathlib import Path
from typing import Any, Callable, Set, Tuple, Type

import pytest

from analysis_service_core.src.config import Config, EnvVar


@pytest.fixture
def setup_required_env_vars(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    datasets_dir = tmp_path / "datasets"
    echolalia_dir = tmp_path / "echolalia"
    datasets_dir.mkdir()
    echolalia_dir.mkdir()

    monkeypatch.setenv("DATASETS_DIR", str(datasets_dir))
    monkeypatch.setenv("ECHOLALIA_DIR", str(echolalia_dir))


@pytest.fixture
def broken_required_env_vars(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATASETS_DIR", "/tmp/datasets")
    monkeypatch.setenv("ECHOLALIA_DIR", "/tmp/echolalia")


type ConfigFactory = Callable[[Set[Tuple[str, Any, Type]]], Config]


@pytest.fixture
def config_factory(
    setup_required_env_vars, monkeypatch: pytest.MonkeyPatch  # noqa: F841
) -> ConfigFactory:
    def get_config(env_vars: Set[Tuple[str, Any, Type]]) -> Config:
        for key, val, _ in env_vars:
            monkeypatch.setenv(key, str(val))

        return Config({EnvVar(key=key, type=t) for key, _, t in env_vars})

    return get_config


def test_config_missing_required():
    with pytest.raises(ValueError):
        config = Config()  # noqa: F841


def test_required_config_exists(broken_required_env_vars):
    with pytest.raises(FileNotFoundError):
        config = Config()  # noqa: F841


def test_proper_config(config_factory: ConfigFactory):
    config = config_factory(
        {
            ("MY_STR", "my_string", str),
            ("MY_INT", "123", int),
            ("MY_FLOAT", "12.25", float),
            ("MY_BOOL", "true", bool),
        }
    )

    assert type(config.get("ECHOLALIA_DIR")).__name__ == "PosixPath"
    assert config.get("MY_STR") == "my_string"
    assert config.get("MY_INT") == 123
    assert config.get("MY_FLOAT") == 12.25
    assert type(config.get("MY_BOOL")) == bool
    assert config.get("MY_BOOL")
