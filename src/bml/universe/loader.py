"""Load and validate the investable universe from a YAML file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from bml.universe.asset import Asset
from bml.universe.universe import Universe


class UniverseLoaderError(RuntimeError):
    """Raised when the universe file cannot be loaded or validated."""


class _UniverseFile(BaseModel):
    """Internal Pydantic schema for the YAML root object."""

    assets: list[Asset] = Field(min_length=1)


class UniverseLoader:
    """Load and validate a Universe from a YAML configuration file.

    The default file is shipped with the package at
    `src/bml/config/universe.yaml`. A custom path can be passed for testing
    or alternative configurations.

    Example:
        >>> universe = UniverseLoader.load()  # default
        >>> universe = UniverseLoader.load("path/to/custom.yaml")
    """

    DEFAULT_PATH: Path = Path(__file__).resolve().parent.parent / "config" / "universe.yaml"

    @classmethod
    def load(cls, path: Path | str | None = None) -> Universe:
        """Load and return a validated Universe.

        Args:
            path: Path to a YAML universe file. Defaults to the shipped
                universe.yaml when None.

        Returns:
            A Universe instance with validated assets.

        Raises:
            FileNotFoundError: If the file does not exist.
            UniverseLoaderError: If parsing or validation fails.
            ValueError: If the resulting universe contains duplicate ISINs.
        """
        target = Path(path) if path is not None else cls.DEFAULT_PATH

        if not target.exists():
            raise FileNotFoundError(f"Universe file not found: {target}")

        try:
            with target.open("r", encoding="utf-8") as f:
                raw: Any = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise UniverseLoaderError(f"Invalid YAML in {target}: {exc}") from exc

        if not isinstance(raw, dict):
            raise UniverseLoaderError(f"YAML root must be a mapping, got {type(raw).__name__}")

        try:
            parsed = _UniverseFile.model_validate(raw)
        except ValidationError as exc:
            raise UniverseLoaderError(f"Universe validation failed in {target}:\n{exc}") from exc

        return Universe(parsed.assets)
