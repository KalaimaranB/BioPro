from unittest.mock import MagicMock, patch

import pytest

from karcytics.core import crash_reporting


class _FakePreferences:
    def __init__(self):
        self.data = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value


@pytest.fixture(autouse=True)
def _isolated_state(monkeypatch):
    """Every test gets its own fake preferences store and a reset
    module-level `_initialized` flag, so consent/init state from one test
    never leaks into the next.
    """
    monkeypatch.setattr(crash_reporting, "core_preferences", _FakePreferences())
    monkeypatch.setattr(crash_reporting, "_initialized", False)
    yield
    monkeypatch.setattr(crash_reporting, "_initialized", False)


class TestConsent:
    def test_consent_defaults_to_undecided(self):
        assert crash_reporting.is_consent_given() is None

    def test_set_consent_true_persists_and_is_read_back(self, monkeypatch):
        monkeypatch.setattr(crash_reporting, "get_configured_dsn", lambda: None)
        crash_reporting.set_consent(True)
        assert crash_reporting.is_consent_given() is True

    def test_set_consent_false_persists_and_is_read_back(self):
        crash_reporting.set_consent(False)
        assert crash_reporting.is_consent_given() is False


class TestGetConfiguredDsn:
    def test_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("KARCYTICS_SENTRY_DSN", raising=False)
        assert crash_reporting.get_configured_dsn() is None

    def test_returns_env_value_when_set(self, monkeypatch):
        monkeypatch.setenv("KARCYTICS_SENTRY_DSN", "https://example.invalid/1")
        assert crash_reporting.get_configured_dsn() == "https://example.invalid/1"


class TestInitCrashReporting:
    def test_noop_without_a_configured_dsn(self, monkeypatch):
        monkeypatch.setattr(crash_reporting, "get_configured_dsn", lambda: None)
        crash_reporting.set_consent(True)

        assert crash_reporting.init_crash_reporting() is False
        assert crash_reporting.is_active() is False

    def test_noop_without_consent(self, monkeypatch):
        monkeypatch.setattr(
            crash_reporting, "get_configured_dsn", lambda: "https://example.invalid/1"
        )

        assert crash_reporting.init_crash_reporting() is False
        assert crash_reporting.is_active() is False

    def test_initializes_sentry_when_dsn_and_consent_both_present(self, monkeypatch):
        monkeypatch.setattr(
            crash_reporting, "get_configured_dsn", lambda: "https://example.invalid/1"
        )
        crash_reporting.core_preferences.set(crash_reporting.CONSENT_PREFERENCE_KEY, True)

        mock_sentry = MagicMock()
        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            assert crash_reporting.init_crash_reporting() is True

        assert crash_reporting.is_active() is True
        mock_sentry.init.assert_called_once()
        kwargs = mock_sentry.init.call_args.kwargs
        assert kwargs["dsn"] == "https://example.invalid/1"
        assert kwargs["send_default_pii"] is False
        assert kwargs["include_local_variables"] is False

    def test_set_consent_true_triggers_init_when_dsn_configured(self, monkeypatch):
        monkeypatch.setattr(
            crash_reporting, "get_configured_dsn", lambda: "https://example.invalid/1"
        )
        mock_sentry = MagicMock()
        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            crash_reporting.set_consent(True)

        assert crash_reporting.is_active() is True

    def test_set_consent_false_shuts_down_an_active_client(self, monkeypatch):
        monkeypatch.setattr(
            crash_reporting, "get_configured_dsn", lambda: "https://example.invalid/1"
        )
        mock_sentry = MagicMock()
        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            crash_reporting.set_consent(True)
            assert crash_reporting.is_active() is True

            crash_reporting.set_consent(False)

        assert crash_reporting.is_active() is False


class TestScrubbing:
    def test_scrubs_home_directory_occurrences(self):
        from pathlib import Path

        home = str(Path.home())
        result = crash_reporting._scrub_value(f"loaded from {home}/projects/x")
        assert home not in result
        assert "<home>" in result

    def test_scrubs_absolute_path_ending_in_data_extension(self):
        result = crash_reporting._scrub_value("failed to parse /Volumes/Data/PatientX_Sample3.fcs")
        assert "PatientX_Sample3.fcs" not in result
        assert "<redacted-file>" in result

    def test_leaves_unrelated_strings_untouched(self):
        assert crash_reporting._scrub_value("division by zero") == "division by zero"

    def test_recurses_into_nested_dicts_and_lists(self):
        from pathlib import Path

        home = str(Path.home())
        event = {
            "message": "boom",
            "extra": {"path": f"{home}/data.fcs"},
            "breadcrumbs": [{"message": f"{home}/other.csv"}],
        }

        result = crash_reporting._scrub_value(event)

        assert home not in result["extra"]["path"]
        assert home not in result["breadcrumbs"][0]["message"]
        assert result["message"] == "boom"

    def test_before_send_applies_scrubbing(self):
        from pathlib import Path

        home = str(Path.home())
        event = {"message": f"error in {home}/sample.fcs"}

        result = crash_reporting._before_send(event, {})

        assert home not in result["message"]


class TestCaptureFatalError:
    def test_noop_when_not_active(self):
        # is_active() is False by default in this isolated fixture — must
        # not raise or try to import sentry_sdk at all.
        crash_reporting.capture_fatal_error("boom", None, None, None)

    def test_captures_live_exception_when_available(self, monkeypatch):
        monkeypatch.setattr(crash_reporting, "_initialized", True)
        mock_sentry = MagicMock()
        mock_scope = MagicMock()
        mock_sentry.push_scope.return_value.__enter__.return_value = mock_scope

        exc = ValueError("nope")
        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            crash_reporting.capture_fatal_error("bad transform", exc, "flow_cytometry", None)

        mock_scope.set_tag.assert_called_once_with("plugin_id", "flow_cytometry")
        mock_sentry.capture_exception.assert_called_once_with(exc)
        mock_sentry.capture_message.assert_not_called()

    def test_captures_message_with_traceback_extra_when_no_live_exception(self, monkeypatch):
        monkeypatch.setattr(crash_reporting, "_initialized", True)
        mock_sentry = MagicMock()
        mock_scope = MagicMock()
        mock_sentry.push_scope.return_value.__enter__.return_value = mock_scope

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            crash_reporting.capture_fatal_error(
                "remote failure", None, "flow_cytometry", "Traceback (most recent call last):\n..."
            )

        mock_scope.set_extra.assert_called_once_with(
            "traceback", "Traceback (most recent call last):\n..."
        )
        mock_sentry.capture_message.assert_called_once_with("remote failure", level="fatal")
        mock_sentry.capture_exception.assert_not_called()
