import os
import yaml
import collections.abc
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, TypeVar
from django.core.exceptions import ImproperlyConfigured
from functools import reduce
import operator

# Generic TypeVar for casting function return values
T = TypeVar("T")


class Config:
    """
    A robust, nested configuration loader that deeply merges settings from three sources:
    1. Environment Variables (using `PARENT__CHILD` for nesting)
    2. YAML Configuration File (`config.yaml`)
    3. Hardcoded Default Values

    Raises ImproperlyConfigured if a required setting is not found in any source.
    This class respects case-sensitivity for setting keys to align with Django conventions.
    """

    def __init__(self, config_path: Path, defaults: dict[str, Any] | None = None):
        self._defaults = defaults or {}
        self._yaml_config = self._load_yaml(config_path)
        self._env_config = self._load_from_env()

    def _deep_merge(self, base: dict, new: dict) -> dict:
        """Recursively merges `new` dict into `base` dict."""

        for key, value in new.items():
            if isinstance(base.get(key), dict) and isinstance(
                value, collections.abc.Mapping
            ):
                base[key] = self._deep_merge(base.get(key, {}), value)
            else:
                base[key] = value

        return base

    def _load_yaml(self, config_path: Path) -> dict[str, Any]:
        """Loads the YAML config file if it exists, otherwise returns an empty dict."""

        if not config_path.exists():
            return {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except (yaml.YAMLError, IOError) as e:
            raise ImproperlyConfigured(
                f"Error reading YAML config at {config_path}: {e}"
            )

    def _load_from_env(self) -> dict[str, Any]:
        """Parses environment variables like `AUTH__OTP_TIMEOUT` into a nested dict."""

        env_config = {}
        for key, value in os.environ.items():
            # Split by '__' to create a path for the nested dictionary
            path = key.split("__")
            target = env_config
            # Traverse/create the nested dict structure
            for i, part in enumerate(path):
                if i == len(path) - 1:
                    target[part] = value
                else:
                    target = target.setdefault(part, {})

        return env_config

    def _get_from_path(self, source: dict, path: list[str]) -> Any | None:
        """Safely retrieves a value from a nested dict using a path list."""

        try:
            return reduce(operator.getitem, path, source)
        except (KeyError, TypeError):
            return None

    def get(
        self, key: str, *, cast: Callable[[Any], T] | None = None, required: bool = True
    ) -> T | Any | None:
        """
        Retrieves a configuration value for a given key, supporting dot notation for nesting.

        Example: `config.get("DATABASE.PORT", cast=int)`

        Args:
            key: The name of the setting, using '.' for nesting (e.g., "AUTH.OTP_TIMEOUT").
            cast: An optional callable (e.g., int, bool) to cast the final value.
            required: If True (default), raises ImproperlyConfigured if the key is not found.
                      If False, returns None if the key is not found.

        Returns:
            The configuration value, or None if not found and not required.

        Raises:
            ImproperlyConfigured: If the key is required and not found in any source,
                                  or if casting fails.
        """

        path = key.split(".")

        default_val = self._get_from_path(self._defaults, path)
        yaml_val = self._get_from_path(self._yaml_config, path)
        env_val = self._get_from_path(self._env_config, path)

        # Determine final value based on priority and type
        value = None
        if isinstance(default_val, dict):
            # For dictionaries, perform a deep merge
            merged_val = deepcopy(default_val)
            if isinstance(yaml_val, dict):
                self._deep_merge(merged_val, yaml_val)
            if isinstance(env_val, dict):
                self._deep_merge(merged_val, env_val)
            value = merged_val
        else:
            # For scalar values, prioritize env > yaml > default
            if env_val is not None:
                value = env_val
            elif yaml_val is not None:
                value = yaml_val
            else:
                value = default_val

        if value is None:
            if required:
                raise ImproperlyConfigured(
                    f"Required setting '{key}' is not defined in any source."
                )
            return None

        if cast is None:
            return value

        # Perform smart casting for values that are likely strings (from env)
        if cast is bool and isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        if cast is list and isinstance(value, str):
            return [item.strip() for item in value.split(",")]

        try:
            return cast(value)
        except (ValueError, TypeError) as e:
            raise ImproperlyConfigured(
                f"Failed to cast setting '{key}' with value {value!r} to {
                    cast.__name__
                }. Error: {e}"
            )
