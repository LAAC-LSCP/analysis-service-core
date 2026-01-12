import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Set, Type, Union


@dataclass(frozen=True)
class EnvVar:
    """
    Encapsulates environment variable declarations
    """

    key: str
    type: Type[Path] | Type[str] | Type[int] | Type[float] | Type[bool]


type Value = Union[Path, int, str, float, bool]


@dataclass(frozen=True)
class ValuedEnvVar:
    """
    Encapsulates an environment variable key and its parsed value
    """

    key: str
    value: Value


REQUIRED_ENV_VARS: Set[EnvVar] = {
    EnvVar(key="DATASETS_DIR", type=Path),
    EnvVar(key="ECHOLALIA_DIR", type=Path),
}


class Config:
    """
    Handles loading, validating, and accessing environment variables for the
    application.

    The Config class loads required and optional environment variables, validates their
    presence and types,
    and provides convenient accessors for their values. It supports type conversion
    for Path, str, int, float, and bool,
    and raises informative errors if variables are missing or invalid.

    Example:
        from pathlib import Path
        from analysis_service_core.src.config import Config, EnvVar

        # Suppose you have set the environment variable MY_ENV_VAR=42
        custom_env_vars = {EnvVar(key="MY_ENV_VAR", type=int)}
        config = Config(env_vars=custom_env_vars)
        my_value = config.get("MY_ENV_VAR")  # my_value will be 42 as an int
        dataset_dir = config.dataset_dir     # Uses DATASETS_DIR from environment
    """

    _env_vars: Set[ValuedEnvVar]

    def __init__(self, env_vars: Set[EnvVar] = set(), check_required: bool = True):
        """
        Initializes the Config object by loading and validating environment variables.

        Args:
            env_vars (Set[EnvVar], optional): Additional environment variables to load
                and validate.
            check_required (bool, optional): If True, also checks for required
                environment variables defined in REQUIRED_ENV_VARS.

        Raises:
            ValueError: If a required environment variable is missing or cannot be
                converted to the specified type.
            FileNotFoundError: If a required Path environment variable does not exist.
        """
        self._load(env_vars, check_required)

    def _load(self, env_vars: Set[EnvVar], check_required: bool) -> None:
        self._env_vars = set()

        if check_required:
            env_vars = env_vars.union(REQUIRED_ENV_VARS)

        for env_var in env_vars:
            self._env_vars.add(self._load_env_var(env_var))

    def _load_env_var(self, env_var: EnvVar) -> ValuedEnvVar:
        env_value = os.getenv(env_var.key)

        if env_value is None:
            raise ValueError(
                f"Environment variable \
'{env_var.key}' not found"
            )

        var_type = env_var.type

        value: Value
        if var_type == Path:
            value = Path(env_value)

            if not value.exists():
                raise FileNotFoundError(
                    f"Env var \
'{env_var.key}' corresponds to non-existent path"
                )
        elif var_type == str:
            value = env_value
        elif var_type == int:
            if not env_value.isdigit():
                raise ValueError(
                    f"Cannot convert \
'{env_var.key}' to int"
                )

            value = int(env_value)
        elif var_type == float:
            try:
                float(env_value)
            except Exception:
                raise ValueError(
                    f"Cannot convert \
'{env_value}' to float for '{env_var.key}'"
                )

            value = float(env_value)
        elif var_type == bool:
            value = env_value.lower() in ["yes", "y", "true", "1", "on"]
        else:
            raise ValueError(
                f"env_var type '{str(env_var.type)}' not \
`Path`, `str`, `int`, `float`, or `bool`"
            )

        return ValuedEnvVar(key=env_var.key, value=value)

    def get(self, key: str) -> Any:
        return next(
            (env_var.value for env_var in self._env_vars if env_var.key == key),
            None,
        )

    def set(self, key: str, value: Value) -> None:
        self._env_vars = {env_var for env_var in self._env_vars if env_var.key != key}
        self._env_vars.add(ValuedEnvVar(key=key, value=value))

    @property
    def dataset_dir(self) -> Path:
        return self.get("DATASETS_DIR")

    @property
    def datasets_outputs_dir(self) -> Path:
        return self.get("DATASETS_DIR") / "outputs"

    @property
    def echolalia_dir(self) -> Path:
        return self.get("ECHOLALIA_DIR")

    @property
    def echolalia_outputs_dir(self) -> Path:
        return self.get("ECHOLALIA_DIR") / "outputs"
