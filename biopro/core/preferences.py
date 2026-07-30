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

    def __init__(self) -> None:
        """Initialize the preference manager and load persisted preferences."""
        self.config_dir = AppConfig.APP_DATA_DIR
        self.config_file = self.config_dir / "preferences.json"
        self.data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load preferences from the configured preferences file into the manager."""
        self.data = AtomicJsonFile.load(self.config_file, default={})

    def save(self) -> None:
        """Persist the current preferences to the configured file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not AtomicJsonFile.save(self.config_file, self.data):
            logger.error("Failed to save preferences.")

    def set(self, key: str, value: Any) -> None:
        """Set a preference value and persist the updated preferences.

        Parameters:
                key (str): The preference key.
                value (Any): The value to associate with the key.
        """
        self.data[key] = value
        self.save()  # Auto-save for core UI state

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a preference value by key.

        Parameters:
                key (str): The preference key to retrieve.
                default (Any): The value to return when the key is absent.

        Returns:
                Any: The stored preference value, or `default` when the key is absent.
        """
        return self.data.get(key, default)

    def has(self, key: str) -> bool:
        """Determine whether a preference key exists.

        Parameters:
            key (str): The preference key to check.

        Returns:
            bool: `true` if the key exists, `false` otherwise.
        """
        return key in self.data

    def clear(self) -> None:
        """Clear all stored preferences and persist the updated state."""
        self.data.clear()
        self.save()


# Singleton instance
core_preferences = CorePreferenceManager()
