"""End-to-end test: opening an isolated module through the real
WorkspaceWindow/PluginLoaderManager/GalacticLoader choreography, driving a
real ModuleStatusWidget backed by a real PluginUIDaemon subprocess — not a
mock panel. Proves the existing Ready Gate protocol (panel_ready/data_ready/
begin_async_init), reused unchanged from the in-process path, is genuinely
sufficient to carry an isolated module through open_module() to a visible,
crossfaded Running state. See the Interpreter Isolation Plan's Phase 2.
"""

from unittest.mock import MagicMock, patch

import pytest
from karcytics_sdk.host.module_status_widget import ModuleStatusWidget
from karcytics_sdk.plugin.daemon import PluginUIDaemon

from karcytics.ui.windows.workspace_window import _PAGE_ANALYSIS, WorkspaceWindow


@pytest.fixture
def fast_worker_script(tmp_path):
    script_path = tmp_path / "fast_worker.py"
    code = """
from PyQt6.QtWidgets import QLabel
from karcytics_sdk.plugin.ui_daemon_runtime import run

def build_panel():
    return QLabel("fast")

if __name__ == "__main__":
    run(build_panel)
"""
    script_path.write_text(code, encoding="utf-8")
    return script_path


class TestWorkspaceWindowIsolatedModule:
    @pytest.fixture
    def window(self, qtbot):
        pm = MagicMock()
        pm.data = {"project_name": "Unit Testing"}
        pm.history_manager = MagicMock()

        mm = MagicMock()
        mm.get_available_modules.return_value = [
            {"id": "isolated_test_plugin", "name": "Isolated Test Plugin", "icon": "🧩"}
        ]

        up = MagicMock()
        hub_cb = MagicMock()
        store_cb = MagicMock()

        with patch("karcytics.ui.windows.workspace.hub_manager.HubManager.maybe_start_core_intro"):
            win = WorkspaceWindow(pm, mm, up, store_cb, hub_cb)
            qtbot.addWidget(win)
            return win

    @patch("karcytics.ui.dialogs.error_report.ErrorReportDialog.exec")
    def test_open_isolated_module_reaches_running_via_ready_gate(
        self, mock_err, window, qtbot, fast_worker_script
    ):
        plugin_id = "isolated_test_plugin"

        def factory():
            daemon = PluginUIDaemon.get_instance(plugin_id, daemon_script_path=fast_worker_script)
            return ModuleStatusWidget(daemon, module_name="Isolated Test Plugin")

        window.module_manager.load_module_ui.return_value = factory

        manifest = {
            "id": plugin_id,
            "display_name": "Isolated Test Plugin",
            "name": "Isolated Test Plugin",
            "icon": "🧩",
        }

        try:
            window.plugin_manager.open_module(manifest)

            qtbot.waitUntil(lambda: window.wizard_panel is not None, timeout=5000)
            assert isinstance(window.wizard_panel, ModuleStatusWidget)

            # The Ready Gate must have kept the loader up until the daemon
            # actually reported ready — not crossfaded immediately behind an
            # empty "Spawning..." card.
            qtbot.waitUntil(
                lambda: window.wizard_panel.state == ModuleStatusWidget.STATE_RUNNING, timeout=10000
            )
            qtbot.waitUntil(
                lambda: window.root_stack.currentIndex() == _PAGE_ANALYSIS, timeout=5000
            )

            assert window.current_module_id == plugin_id
            mock_err.assert_not_called()
        finally:
            PluginUIDaemon.stop_instance(plugin_id)
