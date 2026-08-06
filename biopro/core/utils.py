"""Core module."""

import contextlib
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def parse_version(v_str: str) -> tuple[int, int, int]:
    """Parse a version string into a fixed-width three-component tuple.

    Parameters:
        v_str (str): Version string, optionally containing a suffix after a hyphen.

    Returns:
        tuple[int, int, int]: Parsed version components containing exactly the first
        three numeric components, padded with zeros if needed. Returns `(0, 0, 0)`
        when no numeric components can be parsed.
    """
    try:
        if not v_str or not isinstance(v_str, str):
            return (0, 0, 0)
        clean_v = v_str.split("-")[0]
        parts = []
        for p in clean_v.split("."):
            if p.isdigit():
                parts.append(int(p))
            else:
                break
        # Pad to exactly 3 components so "1.0" == "1.0.0"
        while len(parts) < 3:
            parts.append(0)
        # Return exactly the first 3 components
        return (parts[0], parts[1], parts[2])
    except (ValueError, AttributeError):
        return (0, 0, 0)


def sanitize_identifier(identifier: str | None) -> str | None:
    """Sanitize an identifier to prevent path traversal and ensure it's safe for filenames.

    Parameters:
        identifier (str | None): The identifier to sanitize.

    Returns:
        str | None: The sanitized identifier, or None if invalid.
    """
    if not identifier or not isinstance(identifier, str):
        return None

    # Remove any path separators and dangerous characters
    sanitized = identifier.replace("/", "").replace("\\", "").replace("..", "")

    # Only allow alphanumeric, underscore, hyphen, and period
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.")
    sanitized = "".join(c for c in sanitized if c in allowed_chars)

    # Reject if empty after sanitization or starts with a dot (hidden files)
    if not sanitized or sanitized.startswith("."):
        return None

    return sanitized


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
