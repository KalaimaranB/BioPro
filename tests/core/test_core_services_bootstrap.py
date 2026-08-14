"""Tests for karcytics.core.core_services_bootstrap — starts the Hub's
CoreServicesServer and registers the services isolated modules can reach
over it.
"""

import threading
from unittest.mock import MagicMock, patch

import pytest
from karcytics_sdk.host.core_services import CoreServicesClient
from karcytics_sdk.plugin.daemon import PluginUIDaemon
from PyQt6.QtWidgets import QApplication

from karcytics.core.core_services_bootstrap import start_core_services


def _call_while_pumping_gui_thread(client: CoreServicesClient, method: str, **kwargs):
    """Run a CoreServicesClient.call() on a background thread while pumping
    QApplication.processEvents() on the calling (GUI) thread.

    Mirrors how this actually runs in production: an isolated plugin's
    CoreServicesClient lives in a completely separate OS process, so a
    handler that needs the GUI thread (via QtThreadBridge) never has to
    share it with the caller. A same-thread, non-pumped call here would
    deadlock: the handler's QtThreadBridge.run() would block waiting for
    the GUI thread's event loop, which is the very thread stuck inside
    client.call()'s blocking HTTP request.
    """
    outcome: dict = {}

    def _worker():
        try:
            outcome["result"] = client.call(method, **kwargs)
        except Exception as exc:  # noqa: BLE001
            outcome["error"] = exc

    thread = threading.Thread(target=_worker)
    thread.start()
    for _ in range(500):
        if "result" in outcome or "error" in outcome:
            break
        QApplication.processEvents()
        thread.join(timeout=0.02)
    thread.join(timeout=2.0)

    if "error" in outcome:
        raise outcome["error"]
    return outcome["result"]


@pytest.fixture(autouse=True)
def _reset_core_services_port():
    yield
    PluginUIDaemon._core_services_port = None
    PluginUIDaemon._core_services_token = None


def test_start_core_services_starts_a_running_server():
    server = start_core_services()
    try:
        assert server.port > 0
    finally:
        server.stop()


def test_start_core_services_records_port_and_token_on_plugin_ui_daemon():
    server = start_core_services()
    try:
        assert PluginUIDaemon._core_services_port == server.port
        assert PluginUIDaemon._core_services_token == server.token
    finally:
        server.stop()


def test_diagnostics_report_error_handler_forwards_to_diagnostic_engine():
    mock_diagnostics = MagicMock()
    with patch("karcytics.core.diagnostics.diagnostics", mock_diagnostics):
        server = start_core_services()
        try:
            client = CoreServicesClient(server.port, token=server.token)
            result = client.call(
                "diagnostics.report_error", message="boom", plugin_id="flow_cytometry", fatal=True
            )
        finally:
            server.stop()

    assert result == {"status": "ok"}
    mock_diagnostics.report_error.assert_called_once_with(
        message="boom", plugin_id="flow_cytometry", fatal=True
    )


def test_diagnostics_report_error_handler_rejects_wrong_token():
    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token="wrong-token")  # noqa: S106
        with pytest.raises(RuntimeError, match="Unauthorized"):
            client.call("diagnostics.report_error", message="boom")
    finally:
        server.stop()


def test_list_categorized_themes_handler_returns_json_safe_paths(qapp):  # noqa: ARG001
    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        result = client.call("theme.list_categorized_themes")
    finally:
        server.stop()

    assert isinstance(result, dict)
    for themes in result.values():
        for name, path in themes:
            assert isinstance(name, str)
            assert isinstance(path, str)  # not a Path — must survive JSON transport


def test_get_current_colors_handler_returns_the_hub_colors(qapp):  # noqa: ARG001
    """An isolated module's startup theme gate (`ui_daemon_runtime
    ._confirm_hub_theme_or_exit`) calls this before building any UI — it
    must return the Hub's actual live `Colors`, not a stale snapshot.
    """
    from karcytics.ui.theme import Colors

    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        result = client.call("theme.get_current_colors")
    finally:
        server.stop()

    assert isinstance(result, dict)
    assert result  # a real Hub always has at least one color attribute set
    assert result.get("BG_DARKEST") == Colors.BG_DARKEST
    for value in result.values():
        assert isinstance(value, str)


def test_switch_theme_handler_runs_on_the_gui_thread(qapp, tmp_path):  # noqa: ARG001
    """Regression test: load_theme() touches QApplication/widgets directly,
    so the handler must marshal onto the GUI thread via QtThreadBridge
    rather than calling it straight from CoreServicesServer's HTTP thread.
    """
    theme_path = tmp_path / "custom.json"
    theme_path.write_text('{"name": "Custom Test Theme", "BG_DARKEST": "#111111"}')

    from karcytics.ui.theme import Colors
    from karcytics.ui.theme import theme_manager as hub_theme_manager

    # load_theme() mutates two pieces of process-global state: Colors'
    # class attributes and theme_manager.current_theme_name (other widgets,
    # e.g. DNALoader, key behavior off current_theme_name == "Karcytics
    # Default" — leaving it stuck on this test's theme name broke an
    # unrelated test purely from suite ordering, caught the hard way).
    original_bg = Colors.BG_DARKEST
    original_theme_name = hub_theme_manager.current_theme_name
    try:
        server = start_core_services()
        try:
            client = CoreServicesClient(server.port, token=server.token)
            result = _call_while_pumping_gui_thread(
                client, "theme.switch_theme", path=str(theme_path)
            )
        finally:
            server.stop()

        assert result == {"status": "ok"}
        assert Colors.BG_DARKEST == "#111111"
    finally:
        Colors.BG_DARKEST = original_bg
        hub_theme_manager.current_theme_name = original_theme_name


def test_switch_theme_handler_rejects_missing_path(qapp):  # noqa: ARG001
    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        result = _call_while_pumping_gui_thread(client, "theme.switch_theme")
    finally:
        server.stop()

    assert result["status"] == "error"
