"""Pure-logic update checking service for BioPro.

Single Responsibility: checks for core app updates and broadcasts via event bus.
Dependency Inversion: accepts a NetworkUpdater protocol, AppConfig, and event bus
    as constructor arguments — all can be mocked in tests with zero network calls.

No Qt imports — this class is UI-agnostic and fully testable in isolation.
"""

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class NetworkUpdaterProtocol(Protocol):
    """Structural protocol for the network updater dependency.

    Any object with a check_for_core_updates() method satisfies this contract,
    enabling easy mocking in tests without inheriting from a concrete class.
    """

    def check_for_core_updates(self) -> tuple[bool, dict | None]:
        """Return (has_update, core_info_dict_or_None)."""
        ...


class AppConfigProtocol(Protocol):
    """Structural protocol for the config dependency."""

    def get_skipped_update_version(self) -> str | None: ...

    def set_skipped_update_version(self, version: str) -> None: ...


class UpdateChecker:
    """Service that checks for core app updates and notifies the event bus.

    Design:
    - SRP: Only owns update-check logic. UI reactions live in UpdateBannerWidget.
    - DIP: All dependencies injected — never instantiates NetworkUpdater or
      AppConfig internally.
    - OCP: Adding new notification channels (e.g. system tray) only requires
      new event subscribers, not changes here.
    """

    def __init__(self, updater: NetworkUpdaterProtocol, config: AppConfigProtocol, event_bus):
        self._updater = updater
        self._config = config
        self._event_bus = event_bus

    def check_and_notify(self) -> None:
        """Check for updates; emit CORE_UPDATE_AVAILABLE if one is available and not skipped.

        Swallows all exceptions — a network failure must never crash the application.
        """
        try:
            has_update, core_info = self._updater.check_for_core_updates()
        except Exception as e:
            logger.warning(f"Update check failed (network unavailable?): {e}")
            return

        if not has_update or core_info is None:
            return

        remote_version = core_info.get("version", "")
        download_url = core_info.get("download_url", "")

        if self.is_version_skipped(remote_version):
            logger.debug(f"Update v{remote_version} was previously skipped by the user.")
            return

        logger.info(f"Core update available: v{remote_version}")

        from biopro.core.event_bus import BioProEvent

        self._event_bus.emit(BioProEvent.CORE_UPDATE_AVAILABLE, remote_version, download_url)

    def skip_version(self, version: str) -> None:
        """Persist a version skip so check_and_notify() won't fire again for it."""
        self._config.set_skipped_update_version(version)
        logger.info(f"User skipped update v{version}")

    def is_version_skipped(self, version: str) -> bool:
        """Return True if the user has previously elected to skip this exact version."""
        return self._config.get_skipped_update_version() == version
