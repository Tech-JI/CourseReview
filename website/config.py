import collections.abc
import operator
import os
from functools import reduce
from pathlib import Path
from typing import Any, Callable, TypeVar

import yaml
from django.core.exceptions import ImproperlyConfigured

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
        # 1. Load all sources of configuration.
        default_config = defaults or {}
        yaml_config = self._load_yaml(config_path)
        env_config = self._load_from_env()

        # 2. Build the final config by merging sources in the correct order of priority.
        # Start with an empty dict, merge defaults, then yaml, then env.
        self._final_config = {}
        self._deep_merge(self._final_config, default_config)
        self._deep_merge(self._final_config, yaml_config)
        self._deep_merge(self._final_config, env_config)

    def _deep_merge(self, base: dict, new: dict) -> None:
        """Recursively merges `new` dict into `base` dict in place."""

        for key, value in new.items():
            base_value = base.get(key)
            if isinstance(base_value, dict) and isinstance(
                value, collections.abc.Mapping
            ):
                # If both the base and new values for a key are dicts, recurse.
                self._deep_merge(base_value, value)
            else:
                # Otherwise, the new value overwrites the base value.
                base[key] = value

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
            # Skip keys that don't contain our nesting separator to avoid noise
            if "__" not in key:
                # Handle simple top-level keys
                env_config[key] = value
                continue

            path = key.split("__")
            target = env_config
            for part in path[:-1]:  # Iterate through the path to create nested dicts
                target = target.setdefault(part, {})
                if not isinstance(target, dict):
                    raise ImproperlyConfigured(
                        f"Environment variable conflict. '{key}' implies '{
                            part
                        }' is a dictionary, "
                        "but it was previously defined as a scalar value."
                    )

            target[path[-1]] = value

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

        path = key.split(".")

        try:
            value = reduce(operator.getitem, path, self._final_config)
        except (KeyError, TypeError):
            if required:
                raise ImproperlyConfigured(
                    f"Required setting '{key}' is not defined in any source."
                )
            return None

        if cast is not None:
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

        return value
