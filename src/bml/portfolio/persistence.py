"""Persistence helpers for portfolio state (JSON serialization).

This module isolates the I/O concerns from the domain logic. The PortfolioState
class itself remains pure (no file system dependencies), while this module
handles the path conventions and atomic writes.
"""

from __future__ import annotations

import json
from pathlib import Path

from bml.portfolio.models import PortfolioState


# Default location for the portfolio state JSON file.
# Resolved relative to the project root (parent of src/).
DEFAULT_PORTFOLIO_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "portfolios"
    / "portfolio_latest.json"
)


def save_portfolio_state(
    state: PortfolioState,
    path: Path | str | None = None,
) -> Path:
    """Persist a PortfolioState to JSON.

    Uses an atomic write pattern (write to .tmp, then rename) to prevent
    file corruption if the process is killed mid-write.

    Args:
        state: The portfolio state to save.
        path: Target file path. Defaults to DEFAULT_PORTFOLIO_PATH.

    Returns:
        The actual path written to.
    """
    target = Path(path) if path is not None else DEFAULT_PORTFOLIO_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    # Pydantic model_dump_json handles dates, enums, and nested models cleanly
    json_str = state.model_dump_json(indent=2)

    # Atomic write: write to temp, then rename
    tmp_path = target.with_suffix(target.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        f.write(json_str)
    tmp_path.replace(target)

    return target


def load_portfolio_state(path: Path | str | None = None) -> PortfolioState | None:
    """Load a PortfolioState from JSON, or None if the file doesn't exist.

    Args:
        path: Source file path. Defaults to DEFAULT_PORTFOLIO_PATH.

    Returns:
        The loaded PortfolioState, or None if the file is missing.

    Raises:
        ValidationError: If the JSON content doesn't match the schema.
    """
    target = Path(path) if path is not None else DEFAULT_PORTFOLIO_PATH

    if not target.exists():
        return None

    with target.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return PortfolioState.model_validate(data)


def backup_portfolio_state(
    path: Path | str | None = None,
    backup_suffix: str = ".bak",
) -> Path | None:
    """Copy the current portfolio state to a backup file.

    Useful before destructive operations (reset, manual edits).

    Args:
        path: Source file. Defaults to DEFAULT_PORTFOLIO_PATH.
        backup_suffix: Suffix appended to the original filename.

    Returns:
        The path of the backup, or None if the source didn't exist.
    """
    source = Path(path) if path is not None else DEFAULT_PORTFOLIO_PATH

    if not source.exists():
        return None

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = source.with_name(
        f"{source.stem}_{timestamp}{backup_suffix}{source.suffix}"
    )

    import shutil
    shutil.copy2(source, backup_path)
    return backup_path
