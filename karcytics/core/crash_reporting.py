"""Consent-gated crash reporting via Sentry.

Nothing here ever sends anything without an explicit, persisted opt-in
(see `is_consent_given`/`set_consent`) — the tri-state default is
"undecided", not "on". A DSN also has to be configured out of band (via the
`KARCYTICS_SENTRY_DSN` environment variable, not hardcoded here) or this
stays a no-op regardless of consent; there's no bundled project to send to.

`_before_send` exists because this app handles flow-cytometry data, where a
file path is very often also a sample/patient identifier
(`PatientX_Sample3.fcs`) — every string value in an outgoing event is
scrubbed for the user's home directory and any path-like token ending in a
known data-file extension before it leaves the machine. `capture_fatal_error`
additionally disables Sentry's own local-variable capture at init time
(`include_local_variables=False`), which is the bigger leak this string
scrub can't reach: a stack frame's local variables can hold a raw DataFrame
or file path no message-string regex would ever see.

Every event carries the core version as Sentry's `release` field, and a
`plugin_version` tag alongside `plugin_id` whenever the error came from a
plugin currently resolvable via `set_module_manager` — otherwise a crash
report only tells you *what* broke, not *which build*.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from karcytics.core.preferences import core_preferences

logger = logging.getLogger(__name__)

CONSENT_PREFERENCE_KEY = "diagnostics.crash_reporting_enabled"
_DSN_ENV_VAR = "KARCYTICS_SENTRY_DSN"

_DATA_FILE_EXTENSIONS = r"(?:fcs|csv|tsv|xlsx?|karcytics|png|jpe?g|tiff?|json)"
_PATH_LIKE_RE = re.compile(
    rf"(?:[A-Za-z]:\\|~?/)[^\s\"']*?\.{_DATA_FILE_EXTENSIONS}\b", re.IGNORECASE
)

_initialized = False
# Set once from _start_application after ModuleManager is constructed — see
# PluginUIDaemon.set_core_services for the same "set once, read elsewhere"
# shape used for the CoreServicesServer connection. Lets a crash report
# resolve which version of a plugin was actually installed when it fired,
# not just its id. None in headless contexts (tests, CLI tools) — plugin
# version is best-effort there, never required.
_module_manager: Any | None = None


def set_module_manager(module_manager: Any) -> None:
    """Register the live ModuleManager so crash reports can resolve plugin versions."""
    global _module_manager
    _module_manager = module_manager


def _plugin_version(plugin_id: str | None) -> str | None:
    if not plugin_id or _module_manager is None:
        return None
    mod_info = _module_manager.modules.get(plugin_id)
    return mod_info.get("version") if mod_info else None


def _tag_scope(scope: Any, plugin_id: str | None, message: str) -> None:
    if plugin_id:
        scope.set_tag("plugin_id", plugin_id)
        plugin_version = _plugin_version(plugin_id)
        if plugin_version:
            scope.set_tag("plugin_version", plugin_version)
    scope.set_context("karcytics", {"message": message})


def get_configured_dsn() -> str | None:
    """Return the Sentry DSN from the environment, or None if unset.

    Deliberately not a hardcoded constant — this repo has no Sentry project
    of its own to send to; a real deployment supplies its own DSN this way.
    """
    return os.environ.get(_DSN_ENV_VAR) or None


def is_consent_given() -> bool | None:
    """Return the user's crash-reporting consent: True, False, or None (never asked)."""
    value = core_preferences.get(CONSENT_PREFERENCE_KEY)
    return value if isinstance(value, bool) else None


def set_consent(enabled: bool) -> None:
    """Persist the user's crash-reporting consent choice."""
    core_preferences.set(CONSENT_PREFERENCE_KEY, enabled)
    if enabled:
        init_crash_reporting()
    else:
        shutdown_crash_reporting()


def is_active() -> bool:
    """Whether Sentry has actually been initialized this session."""
    return _initialized


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        home = str(Path.home())
        if home and home in value:
            value = value.replace(home, "<home>")
        return _PATH_LIKE_RE.sub("<redacted-file>", value)
    if isinstance(value, dict):
        return {k: _scrub_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    return value


def _before_send(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    return _scrub_value(event)


def init_crash_reporting() -> bool:
    """Initialize Sentry if a DSN is configured and consent has been given.

    Safe to call unconditionally at startup and again whenever consent
    changes — it's a no-op whenever either precondition isn't met, and
    idempotent once active.

    Returns:
        bool: Whether Sentry is active after this call.
    """
    global _initialized

    if _initialized:
        return True

    dsn = get_configured_dsn()
    if not dsn:
        logger.debug("Crash reporting not configured (no %s set).", _DSN_ENV_VAR)
        return False

    if is_consent_given() is not True:
        logger.debug("Crash reporting not enabled (consent not given).")
        return False

    import sentry_sdk

    from karcytics.core.config import AppConfig

    sentry_sdk.init(
        dsn=dsn,
        release=f"karcytics@{AppConfig.CORE_VERSION}",
        send_default_pii=False,
        include_local_variables=False,
        before_send=_before_send,  # type: ignore[arg-type]
    )
    _initialized = True
    logger.info("Crash reporting initialized.")
    return True


def shutdown_crash_reporting() -> None:
    """Stop sending crash reports for the rest of this session."""
    global _initialized
    if not _initialized:
        return

    import sentry_sdk

    sentry_sdk.init(dsn=None)
    _initialized = False


def capture_fatal_error(
    message: str,
    exception: BaseException | None,
    plugin_id: str | None,
    traceback_str: str | None,
) -> None:
    """Report a fatal error to Sentry, if active. A silent no-op otherwise.

    Prefers `sentry_sdk.capture_exception` when a live exception object is
    available (the in-process case — gives Sentry a real, parsed
    stacktrace); falls back to `capture_message` with the pre-formatted
    traceback attached as extra context for the remote/isolated-plugin case,
    where only strings ever cross the wire.
    """
    if not is_active():
        return

    import sentry_sdk

    with sentry_sdk.push_scope() as scope:
        _tag_scope(scope, plugin_id, message)

        if exception is not None:
            sentry_sdk.capture_exception(exception)
            return

        if traceback_str:
            scope.set_extra("traceback", traceback_str)
        sentry_sdk.capture_message(message, level="fatal")


def capture_error_data(error_data: dict[str, Any]) -> bool:
    """Send an already-built `DiagnosticEngine` `error_data` dict to Sentry.

    For `ErrorReportDialog`'s explicit "send this report" action: by the
    time a user opts in from that dialog, the error has already crossed the
    diagnostics event bus as a plain dict — there's no live exception object
    left to hand `capture_exception`, only its string form, so this always
    takes the `capture_message` path `capture_fatal_error` falls back to.

    Returns:
        bool: Whether anything was actually sent — False when crash
        reporting isn't active (no DSN configured, or consent not granted).
    """
    if not is_active():
        return False

    import sentry_sdk

    with sentry_sdk.push_scope() as scope:
        plugin_id = error_data.get("plugin_id")
        message = error_data.get("message", "")
        _tag_scope(scope, plugin_id, message)

        traceback_str = error_data.get("traceback")
        if traceback_str:
            scope.set_extra("traceback", traceback_str)
        sentry_sdk.capture_message(message, level="error")

    return True
