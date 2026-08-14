"""Tests for karcytics.core.core_services_bootstrap — starts the Hub's
CoreServicesServer and registers the services isolated modules can reach
over it.
"""

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from karcytics_sdk.host.core_services import CoreServicesClient
from karcytics_sdk.plugin.daemon import PluginUIDaemon
from PyQt6.QtWidgets import QApplication

from karcytics.core.core_services_bootstrap import set_active_project_manager, start_core_services


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


@pytest.fixture(autouse=True)
def _reset_active_project_manager():
    yield
    set_active_project_manager(None)


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


def test_get_about_karcytics_handler_matches_the_shared_source():
    from karcytics.core.about_info import KARCYTICS_ABOUT

    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        result = client.call("menu.get_about_karcytics")
    finally:
        server.stop()

    assert result == KARCYTICS_ABOUT
    for value in result.values():
        assert isinstance(value, str)  # JSON-safe


def test_get_about_developer_handler_matches_the_shared_source():
    from karcytics.core.about_info import DEVELOPER_ABOUT

    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        result = client.call("menu.get_about_developer")
    finally:
        server.stop()

    assert result == DEVELOPER_ABOUT
    for value in result.values():
        assert isinstance(value, str)  # JSON-safe


def test_project_get_info_returns_none_without_an_active_project():
    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        result = client.call("project.get_info")
    finally:
        server.stop()

    assert result is None


def test_project_get_info_returns_the_active_projects_paths(tmp_path):
    mock_pm = MagicMock()
    mock_pm.project_dir = tmp_path
    mock_pm.assets_dir = tmp_path / "assets"
    mock_pm.project_name = "My Project"
    set_active_project_manager(mock_pm)

    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        result = client.call("project.get_info")
    finally:
        server.stop()

    assert result == {
        "project_dir": str(tmp_path),
        "assets_dir": str(tmp_path / "assets"),
        "project_name": "My Project",
    }


def test_project_add_image_raises_without_an_active_project():
    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        with pytest.raises(RuntimeError, match="No project is currently open"):
            client.call("project.add_image", filepath="/x.fcs", copy_to_workspace=True)
    finally:
        server.stop()


def test_project_add_image_forwards_to_the_active_project_manager():
    mock_pm = MagicMock()
    mock_pm.add_image.return_value = "deadbeef"
    set_active_project_manager(mock_pm)

    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        result = client.call(
            "project.add_image", filepath="/x.fcs", copy_to_workspace=True, subfolder="raw"
        )
    finally:
        server.stop()

    assert result == "deadbeef"
    mock_pm.add_image.assert_called_once_with("/x.fcs", True, "raw")


def test_project_get_asset_path_returns_none_without_an_active_project():
    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        result = client.call("project.get_asset_path", file_hash="abc")
    finally:
        server.stop()

    assert result is None


def test_project_get_asset_path_returns_a_json_safe_string(tmp_path):
    resolved = tmp_path / "sample.fcs"
    mock_pm = MagicMock()
    mock_pm.get_asset_path.return_value = resolved
    set_active_project_manager(mock_pm)

    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        result = client.call("project.get_asset_path", file_hash="abc")
    finally:
        server.stop()

    assert result == str(resolved)  # not a Path — must survive JSON transport


def test_project_save_and_load_workflow_payload_forward_to_the_active_project_manager():
    mock_pm = MagicMock()
    mock_pm.save_workflow.return_value = "flow_cytometry_wf.json"
    mock_pm.load_workflow_payload.return_value = {"steps": []}
    set_active_project_manager(mock_pm)

    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        new_filename = client.call(
            "project.save_workflow",
            module_id="flow_cytometry",
            payload={"a": 1},
            metadata={"note": "x"},
            filename="wf",
            attachments=[],
        )
        payload = client.call("project.load_workflow_payload", filename=new_filename)
    finally:
        server.stop()

    assert new_filename == "flow_cytometry_wf.json"
    assert payload == {"steps": []}
    mock_pm.save_workflow.assert_called_once_with(
        module_id="flow_cytometry",
        payload={"a": 1},
        metadata={"note": "x"},
        filename="wf",
        attachments=[],
    )
    mock_pm.load_workflow_payload.assert_called_once_with("flow_cytometry_wf.json")


def test_project_attach_workflow_file_forwards_kwargs():
    mock_pm = MagicMock()
    mock_pm.attach_workflow_file.return_value = {"key": "raw_fcs"}
    set_active_project_manager(mock_pm)

    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        result = client.call(
            "project.attach_workflow_file",
            wf_filename="wf.json",
            source_path="/tmp/att.fcs",
            key="raw_fcs",
        )
    finally:
        server.stop()

    assert result == {"key": "raw_fcs"}
    mock_pm.attach_workflow_file.assert_called_once_with(
        wf_filename="wf.json",
        source_path="/tmp/att.fcs",
        key="raw_fcs",
        description="",
        mime_hint="application/octet-stream",
    )


def test_project_list_workflows_and_load_attachments_return_empty_without_an_active_project():
    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        assert client.call("project.list_workflows") == []
        assert client.call("project.load_attachments", filename="wf.json") == []
    finally:
        server.stop()


def test_project_list_workflows_and_load_attachments_forward_to_the_active_project_manager():
    mock_pm = MagicMock()
    mock_pm.workflows.list_all.return_value = [{"filename": "wf.json"}]
    mock_pm.workflows.load_attachments.return_value = [{"key": "raw_fcs"}]
    set_active_project_manager(mock_pm)

    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        workflows = client.call("project.list_workflows")
        attachments = client.call("project.load_attachments", filename="wf.json")
    finally:
        server.stop()

    assert workflows == [{"filename": "wf.json"}]
    assert attachments == [{"key": "raw_fcs"}]


def test_project_add_image_really_copies_the_file_into_the_real_projects_assets_dir(tmp_path):
    """Closes the loop on the actual regression report: an isolated
    module's file import ending up in the project's real `assets/` folder,
    not just a mock recording the right call. Uses the real `ProjectManager`
    (hashing, copy-to-workspace, `project.karcytics` persistence and all),
    exactly as the Hub itself would have one open.
    """
    from karcytics.core.projects.manager import ProjectManager

    project_dir = tmp_path / "my_project"
    pm = ProjectManager(project_dir)
    pm.create_new("My Project")

    source_file = tmp_path / "sample.fcs"
    source_file.write_bytes(b"not a real fcs file, just needs bytes to hash")

    set_active_project_manager(pm)

    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        file_hash = client.call(
            "project.add_image", filepath=str(source_file), copy_to_workspace=True
        )
        resolved = client.call("project.get_asset_path", file_hash=file_hash)
    finally:
        server.stop()

    assert resolved is not None
    copied_path = Path(resolved)
    assert copied_path.exists()
    assert copied_path.parent == pm.assets_dir
    assert copied_path.read_bytes() == source_file.read_bytes()
    # add_image() also persists to project.karcytics — proves the RPC path
    # went through the real ProjectManager.add_image(), not just AssetManager
    # in isolation, so the Hub's own project state stays consistent too.
    assert file_hash in pm.data["assets"]


def test_set_active_project_manager_replaces_the_previous_reference():
    """Regression coverage for switching projects: a second call must fully
    replace the first, not merge with or append to it — the isolated module
    should see exactly the currently open project, never a stale one.
    """
    first_pm = MagicMock()
    first_pm.project_dir = "/first"
    first_pm.assets_dir = "/first/assets"
    first_pm.project_name = "First"
    second_pm = MagicMock()
    second_pm.project_dir = "/second"
    second_pm.assets_dir = "/second/assets"
    second_pm.project_name = "Second"

    set_active_project_manager(first_pm)
    set_active_project_manager(second_pm)

    server = start_core_services()
    try:
        client = CoreServicesClient(server.port, token=server.token)
        result = client.call("project.get_info")
    finally:
        server.stop()

    assert result["project_name"] == "Second"
