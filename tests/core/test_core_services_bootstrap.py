"""Tests for karcytics.core.core_services_bootstrap — starts the Hub's
CoreServicesServer and registers the services isolated modules can reach
over it.
"""

from unittest.mock import MagicMock, patch

import pytest
from karcytics_sdk.host.core_services import CoreServicesClient
from karcytics_sdk.plugin.daemon import PluginUIDaemon

from karcytics.core.core_services_bootstrap import start_core_services


@pytest.fixture(autouse=True)
def _reset_core_services_port():
    yield
    PluginUIDaemon._core_services_port = None


def test_start_core_services_starts_a_running_server():
    server = start_core_services()
    try:
        assert server.port > 0
    finally:
        server.stop()


def test_start_core_services_records_port_on_plugin_ui_daemon():
    server = start_core_services()
    try:
        assert PluginUIDaemon._core_services_port == server.port
    finally:
        server.stop()


def test_diagnostics_report_error_handler_forwards_to_diagnostic_engine():
    mock_diagnostics = MagicMock()
    with patch("karcytics.core.diagnostics.diagnostics", mock_diagnostics):
        server = start_core_services()
        try:
            client = CoreServicesClient(server.port)
            result = client.call(
                "diagnostics.report_error", message="boom", plugin_id="flow_cytometry", fatal=True
            )
        finally:
            server.stop()

    assert result == {"status": "ok"}
    mock_diagnostics.report_error.assert_called_once_with(
        message="boom", plugin_id="flow_cytometry", fatal=True
    )
