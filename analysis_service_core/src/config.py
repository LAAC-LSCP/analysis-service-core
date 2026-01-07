import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Set, Type, Union


@dataclass(frozen=True)
class EnvVar:
    key: str
    type: Type[Path] | Type[str] | Type[int] | Type[float]


type Value = Union[Path, int, str, float]


@dataclass(frozen=True)
class ValuedEnvVar:
    key: str
    value: Value


REQUIRED_ENV_VARS: Set[EnvVar] = {
    EnvVar(key="DATASETS_DIR", type=Path),
    EnvVar(key="ECHOLALIA_DIR", type=Path),
}


class Config:
    _env_vars: Set[ValuedEnvVar]

    def __init__(self, env_vars: Set[EnvVar] = set(), check_required: bool = True):
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
                raise ValueError(
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
            if not env_value.isdecimal():
                raise ValueError(
                    f"Cannot convert \
'{env_value}' to float for '{env_var.key}'"
                )

            value = float(env_value)
        else:
            raise ValueError(
                f"env_var type '{str(env_var.type)}' not \
`Path`, `str`, `int` or `float`"
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
    def echolalia_dir(self) -> Path:
        return self.get("ECHOLALIA_DIR")

    @property
    def echolalia_outputs_dir(self) -> Path:
        return self.get("ECHOLALIA_DIR") / "outputs"
