import contextlib
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AtomicJsonFile:
    """Safe, atomic JSON file reading and writing utility.

    Prevents file corruption by writing to a temporary file first,
    then atomically replacing the target file.
    """

    @staticmethod
    def load(filepath: Path | str, default: Any = None) -> Any:
        """Load JSON from a file.

        Args:
            filepath: Path to the JSON file.
            default: Value to return if the file does not exist or is corrupted.

        Returns:
            The parsed JSON data, or the default value on failure.
        """
        path = Path(filepath)
        if not path.exists():
            return default if default is not None else {}

        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load JSON from {path}: {e}")
            return default if default is not None else {}

    @staticmethod
    def save(filepath: Path | str, data: Any, indent: int | None = 4) -> bool:
        """Save data as JSON atomically.

        Args:
            filepath: Target path for the JSON file.
            data: Data to serialize.
            indent: JSON indentation level.

        Returns:
            True if successful, False otherwise.
        """
        path = Path(filepath)
        temp_path = path.with_suffix(".tmp")

        try:
            # Ensure parent directories exist
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temp file first
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent)
                f.flush()
                os.fsync(f.fileno())

            # Atomically replace target file
            os.replace(temp_path, path)
            return True
        except Exception as e:
            logger.error(f"Failed to atomically save JSON to {path}: {e}")
            if temp_path.exists():
                with contextlib.suppress(OSError):
                    temp_path.unlink()
            return False
