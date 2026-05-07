"""Core Preference Manager for BioPro."""

import json
import logging
from pathlib import Path
from typing import Any

from biopro_sdk.core.preferences import PreferenceManagerProtocol

logger = logging.getLogger(__name__)


class CorePreferenceManager(PreferenceManagerProtocol):
    """Manages UI layout and visual preferences for the core application.

    Stores settings in ~/.biopro/preferences.json, separating UI state
    from global system config.
    """

    def __init__(self):
        self.config_dir = Path.home() / ".biopro"
        self.config_file = self.config_dir / "preferences.json"
        self.data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load preferences: {e}")
                self.data = {}
        else:
            self.data = {}

    def save(self) -> None:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()  # Auto-save for core UI state

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def has(self, key: str) -> bool:
        return key in self.data

    def clear(self) -> None:
        self.data.clear()
        self.save()


# Singleton instance
core_preferences = CorePreferenceManager()
