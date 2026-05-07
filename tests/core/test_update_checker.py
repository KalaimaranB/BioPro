"""Unit tests for the UpdateChecker service.

These tests are written RED-first (TDD) - they define the contract that
UpdateChecker must satisfy, with zero Qt and zero real network calls.
"""

from unittest.mock import MagicMock

import pytest

# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_config(tmp_path):
    """A real AppConfig backed by a temp dir so skip persistence is testable."""
    from biopro.core.config import AppConfig

    config = AppConfig.__new__(AppConfig)
    config.config_dir = tmp_path / ".biopro"
    config.config_file = config.config_dir / "config.json"
    config.data = {"recent_projects": [], "ai_enabled": True}
    return config


@pytest.fixture
def mock_updater_with_update():
    """A NetworkUpdater stub that reports an available update."""
    updater = MagicMock()
    updater.check_for_core_updates.return_value = (
        True,
        {"version": "2.0.0", "download_url": "https://github.com/KalaimaranB/BioPro/releases"},
    )
    return updater


@pytest.fixture
def mock_updater_up_to_date():
    """A NetworkUpdater stub that reports the app is up to date."""
    updater = MagicMock()
    updater.check_for_core_updates.return_value = (False, None)
    return updater


@pytest.fixture
def mock_event_bus():
    """A clean mock event bus for assertions."""
    return MagicMock()


# ─── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestUpdateCheckerEmitsEvent:
    """UpdateChecker.check_and_notify() must emit CORE_UPDATE_AVAILABLE when an update is available."""

    def test_emits_event_when_update_available(
        self, mock_updater_with_update, mock_config, mock_event_bus
    ):
        from biopro.core.event_bus import BioProEvent
        from biopro.core.update_checker import UpdateChecker

        checker = UpdateChecker(mock_updater_with_update, mock_config, mock_event_bus)
        checker.check_and_notify()

        mock_event_bus.emit.assert_called_once_with(
            BioProEvent.CORE_UPDATE_AVAILABLE,
            "2.0.0",
            "https://github.com/KalaimaranB/BioPro/releases",
        )

    def test_no_emit_when_up_to_date(self, mock_updater_up_to_date, mock_config, mock_event_bus):
        from biopro.core.update_checker import UpdateChecker

        checker = UpdateChecker(mock_updater_up_to_date, mock_config, mock_event_bus)
        checker.check_and_notify()

        mock_event_bus.emit.assert_not_called()

    def test_no_emit_when_version_is_skipped(
        self, mock_updater_with_update, mock_config, mock_event_bus
    ):
        from biopro.core.update_checker import UpdateChecker

        # Pre-skip the version that the updater will report
        mock_config.data["skipped_update_version"] = "2.0.0"

        checker = UpdateChecker(mock_updater_with_update, mock_config, mock_event_bus)
        checker.check_and_notify()

        mock_event_bus.emit.assert_not_called()

    def test_emits_when_different_version_than_skipped(
        self, mock_updater_with_update, mock_config, mock_event_bus
    ):
        """If a newer version ships after the user skipped an old one, notify again."""
        from biopro.core.event_bus import BioProEvent
        from biopro.core.update_checker import UpdateChecker

        # User previously skipped 1.5.0, but now 2.0.0 is out
        mock_config.data["skipped_update_version"] = "1.5.0"

        checker = UpdateChecker(mock_updater_with_update, mock_config, mock_event_bus)
        checker.check_and_notify()

        mock_event_bus.emit.assert_called_once_with(
            BioProEvent.CORE_UPDATE_AVAILABLE,
            "2.0.0",
            "https://github.com/KalaimaranB/BioPro/releases",
        )

    def test_no_emit_when_updater_raises(self, mock_config, mock_event_bus):
        """UpdateChecker must swallow network errors gracefully — never crash the app."""
        from biopro.core.update_checker import UpdateChecker

        broken_updater = MagicMock()
        broken_updater.check_for_core_updates.side_effect = Exception("Network unreachable")

        checker = UpdateChecker(broken_updater, mock_config, mock_event_bus)
        checker.check_and_notify()  # Must NOT raise

        mock_event_bus.emit.assert_not_called()


@pytest.mark.unit
class TestUpdateCheckerSkipVersion:
    """UpdateChecker.skip_version() must persist and be query-able."""

    def test_skip_version_persists_to_config(
        self, mock_updater_up_to_date, mock_config, mock_event_bus
    ):
        from biopro.core.update_checker import UpdateChecker

        checker = UpdateChecker(mock_updater_up_to_date, mock_config, mock_event_bus)
        checker.skip_version("2.0.0")

        assert mock_config.get_skipped_update_version() == "2.0.0"

    def test_is_version_skipped_false_for_unset(
        self, mock_updater_up_to_date, mock_config, mock_event_bus
    ):
        from biopro.core.update_checker import UpdateChecker

        checker = UpdateChecker(mock_updater_up_to_date, mock_config, mock_event_bus)

        assert checker.is_version_skipped("2.0.0") is False

    def test_is_version_skipped_true_after_skip(
        self, mock_updater_up_to_date, mock_config, mock_event_bus
    ):
        from biopro.core.update_checker import UpdateChecker

        checker = UpdateChecker(mock_updater_up_to_date, mock_config, mock_event_bus)
        checker.skip_version("2.0.0")

        assert checker.is_version_skipped("2.0.0") is True

    def test_is_version_skipped_false_for_different_version(
        self, mock_updater_up_to_date, mock_config, mock_event_bus
    ):
        from biopro.core.update_checker import UpdateChecker

        checker = UpdateChecker(mock_updater_up_to_date, mock_config, mock_event_bus)
        checker.skip_version("1.5.0")

        # A newer version should not be considered skipped
        assert checker.is_version_skipped("2.0.0") is False
