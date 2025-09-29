import os
import yaml
from pathlib import Path
from typing import Any, Callable, TypeVar
from django.core.exceptions import ImproperlyConfigured
from functools import reduce
import operator
import collections.abc

# Generic TypeVar for casting function return values
T = TypeVar("T")


class Config:
    """
    A robust, nested configuration loader that deeply merges settings from three sources:
    1. Environment Variables (using `PARENT__CHILD` for nesting)
    2. YAML Configuration File (`config.yaml`)
    3. Hardcoded Default Values

    Raises ImproperlyConfigured if a required setting is not found in any source.
    """

    def __init__(self, config_path: Path, defaults: dict[str, Any] | None = None):
        # 1. Start with normalized defaults
        self._final_config = self._normalize_keys_to_lower(defaults or {})

        # 2. Load and merge normalized YAML config
        yaml_config = self._normalize_keys_to_lower(self._load_yaml(config_path))
        self._final_config = self._deep_merge(self._final_config, yaml_config)

        # 3. Load and merge environment variables (already produces lowercase keys)
        env_config = self._load_from_env()
        self._final_config = self._deep_merge(self._final_config, env_config)

    def _normalize_keys_to_lower(self, obj: Any) -> Any:
        """Recursively converts all dictionary keys in an object to lowercase."""

        if isinstance(obj, dict):
            return {
                str(key).lower(): self._normalize_keys_to_lower(value)
                for key, value in obj.items()
            }
        if isinstance(obj, list):
            return [self._normalize_keys_to_lower(item) for item in obj]

        return obj

    def _deep_merge(self, base_dict: dict, new_dict: dict) -> dict:
        """Recursively merges new_dict into base_dict."""

        for key, value in new_dict.items():
            if isinstance(base_dict.get(key), dict) and isinstance(
                value, collections.abc.Mapping
            ):
                base_dict[key] = self._deep_merge(base_dict[key], value)
            else:
                base_dict[key] = value

        return base_dict

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
            path = key.lower().split("__")
            target = env_config
            # Traverse/create the nested dict structure
            for i, part in enumerate(path):
                if i == len(path) - 1:
                    target[part] = value
                else:
                    target = target.setdefault(part, {})

        return env_config

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

        path = key.lower().split(".")
        try:
            value = reduce(operator.getitem, path, self._final_config)
        except (KeyError, TypeError):
            if required:
                raise ImproperlyConfigured(
                    f"Required setting '{key}' is not defined in any source."
                )
            return None

        if cast is None:
            return value

        # Since env vars are strings, perform smart casting
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
