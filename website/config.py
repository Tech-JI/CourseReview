import os
import yaml
from pathlib import Path
from typing import Any, Callable, TypeVar
from django.core.exceptions import ImproperlyConfigured
from functools import reduce
import operator

# Generic TypeVar for casting function return values
T = TypeVar("T")


class Config:
    """
    A centralized, nested configuration loader with a defined priority order:
    1. Environment Variables (using `PARENT__CHILD` for nesting)
    2. YAML Configuration File (`config.yaml`)
    3. Hardcoded Default Values

    Raises ImproperlyConfigured if a required setting is not found in any source.
    """

    def __init__(self, config_path: Path, defaults: dict[str, Any] | None = None):
        self._yaml_config = self._load_yaml(config_path)
        self._defaults = defaults or {}

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

    def _get_nested_val(
        self, source_dict: dict[str, Any], path: list[str]
    ) -> Any | None:
        """Safely retrieves a nested value from a dictionary using a path list."""

        try:
            return reduce(operator.getitem, path, source_dict)
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

        # 1. Check Environment Variables (e.g., AUTH.OTP_TIMEOUT -> AUTH__OTP_TIMEOUT)
        env_key = key.upper().replace(".", "__")
        if (env_val := os.environ.get(env_key)) is not None:
            value, source = env_val, f"environment variable ({env_key})"
        else:
            path = key.split(".")
            # 2. Check YAML Config
            if (yaml_val := self._get_nested_val(self._yaml_config, path)) is not None:
                value, source = yaml_val, "config.yaml"
            # 3. Check Defaults
            elif (
                default_val := self._get_nested_val(self._defaults, path)
            ) is not None:
                value, source = default_val, "default value"
            else:
                if required:
                    raise ImproperlyConfigured(
                        f"Required setting '{key}' is not defined in any source."
                    )
                return None

        if cast is None:
            return value

        if source.startswith("environment"):
            if cast is bool:
                return value.lower() in ("true", "1", "yes")
            if cast is list:
                return [item.strip() for item in value.split(",")]

        try:
            return cast(value)
        except (ValueError, TypeError) as e:
            raise ImproperlyConfigured(
                f"Failed to cast setting '{key}' from {source} with value '{
                    value!r
                }' to {cast.__name__}. Error: {e}"
            )
