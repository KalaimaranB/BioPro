"""Core Preference Manager for BioPro."""

import logging
from typing import Any

from biopro_sdk.plugin import PreferenceManagerProtocol

from biopro.core.config import AppConfig
from biopro.core.utils import AtomicJsonFile

logger = logging.getLogger(__name__)


class CorePreferenceManager(PreferenceManagerProtocol):
    """Manages UI layout and visual preferences for the core application.

    Stores settings in ~/.biopro/preferences.json, separating UI state
    from global system config.
    """

    def __init__(self):
        self.config_dir = AppConfig.APP_DATA_DIR
        self.config_file = self.config_dir / "preferences.json"
        self.data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        self.data = AtomicJsonFile.load(self.config_file, default={})

    def save(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not AtomicJsonFile.save(self.config_file, self.data):
            logger.error("Failed to save preferences.")

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
