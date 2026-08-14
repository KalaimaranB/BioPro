"""Start the CoreServicesServer and register loopback bridge services for isolated modules.

Task scheduling is deliberately *not* exposed here. An isolated module runs
its own local task scheduler inside its own process (see the SDK's
`ui_daemon_runtime` and its `PluginContext`-injected services) — routing
every analysis run through IPC to the Hub would add latency for no
isolation benefit, per the same reasoning already applied when Flow
Cytometry's `ui_daemon.py` was first prototyped. Only state that genuinely
lives in the Hub (diagnostics reporting, theme queries, and project I/O —
see `set_active_project_manager`) belongs behind this loopback bridge.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from karcytics_sdk.host.core_services import CoreServicesServer
from karcytics_sdk.plugin.daemon import PluginUIDaemon

logger = logging.getLogger(__name__)

_active_project_manager_lock = threading.Lock()
_active_project_manager: Any | None = None
# Guards every project.* handler below that mutates ProjectManager.data or
# writes it to disk (add_image, save_workflow, attach_workflow_file).
# CoreServicesServer answers each request on its own ThreadingHTTPServer
# thread, so two isolated modules' asset imports (or one module racing the
# Hub's own UI-thread project I/O) could otherwise interleave a
# read-modify-write of the same in-memory dict and corrupt project.karcytics
# on save. ProjectManager itself has no such lock — it was never built to be
# called from more than one thread at a time — so this is the minimum
# needed now that CoreServicesServer is a second, genuinely concurrent
# caller.
_project_write_lock = threading.Lock()


def set_active_project_manager(project_manager: Any | None) -> None:
    """Record the Hub's currently open project.

    This allows `project.*` handlers below to reach it.

    Call with the real `ProjectManager` when `WorkspaceWindow` opens a
    project (`project_launcher.py`'s `_launch_workspace`) and with `None`
    when it closes (`WorkspaceWindow.return_to_hub`). Not a live object
    reference `ProjectManager` itself knows about — same relationship
    `theme.get_current_colors` has to `Colors`, just for something that
    changes per-project instead of being a true process-wide singleton.
    """
    global _active_project_manager
    with _active_project_manager_lock:
        _active_project_manager = project_manager


def _get_active_project_manager() -> Any | None:
    with _active_project_manager_lock:
        return _active_project_manager


def _handle_get_about_karcytics(_kwargs: dict[str, Any]) -> dict[str, str]:
    from karcytics.core.about_info import KARCYTICS_ABOUT

    return dict(KARCYTICS_ABOUT)


def _handle_get_about_developer(_kwargs: dict[str, Any]) -> dict[str, str]:
    from karcytics.core.about_info import DEVELOPER_ABOUT

    return dict(DEVELOPER_ABOUT)


def current_theme_colors() -> dict[str, str]:
    """Snapshot every string color attribute currently on the Hub's `Colors` class.

    Shared by `theme.get_current_colors` below and `PluginLoaderFactory
    ._wire_theme_sync`'s live push on every subsequent Hub theme change — one
    definition of "what a theme is" for isolated modules, not two that could
    drift apart.
    """
    from karcytics.ui.theme import Colors

    return {
        k: getattr(Colors, k)
        for k in dir(Colors)
        if not k.startswith("_") and isinstance(getattr(Colors, k), str)
    }


def start_core_services() -> CoreServicesServer:  # noqa: C901, PLR0915
    """Start the Hub's `CoreServicesServer` and register its handlers.

    Records the server port on `PluginUIDaemon` so every isolated module spawned
    from here on can reach it.

    Call once, early in Hub startup. The caller owns the returned server's
    lifetime and must call `.stop()` on shutdown (e.g. via `QApplication
    .aboutToQuit`).
    """
    from karcytics_sdk.host.qt_bridge import QtThreadBridge

    from karcytics.core.diagnostics import diagnostics
    from karcytics.ui.theme import theme_manager as hub_theme_manager

    server = CoreServicesServer()
    qt_bridge = QtThreadBridge()

    def _handle_report_error(kwargs: dict[str, Any]) -> dict[str, str]:
        diagnostics.report_error(
            message=kwargs.get("message", ""),
            plugin_id=kwargs.get("plugin_id"),
            fatal=kwargs.get("fatal", False),
        )
        return {"status": "ok"}

    def _handle_get_current_colors(_kwargs: dict[str, Any]) -> dict[str, str]:
        # Read-only attribute snapshot, no widget touched — safe to run
        # directly on the CoreServicesServer handler thread.
        return current_theme_colors()

    def _handle_list_themes(_kwargs: dict[str, Any]) -> dict[str, list[list[str]]]:
        # Read-only disk/dict work, no widget touched — safe to run directly
        # on the CoreServicesServer handler thread, unlike switch_theme below.
        categorized = hub_theme_manager.get_categorized_themes()
        return {
            category: [[name, str(path)] for name, path in themes]
            for category, themes in categorized.items()
        }

    def _handle_switch_theme(kwargs: dict[str, Any]) -> dict[str, str]:
        from pathlib import Path

        path = kwargs.get("path")
        if not path:
            return {"status": "error", "message": "Missing required 'path'."}

        def _switch() -> bool:
            # load_theme() calls QApplication.setStyleSheet() and restyles
            # every tracked widget directly — must run on the GUI thread.
            return hub_theme_manager.load_theme(Path(path))

        ok = qt_bridge.run(_switch)
        return {"status": "ok" if ok else "error"}

    def _handle_project_get_info(_kwargs: dict[str, Any]) -> dict[str, str] | None:
        pm = _get_active_project_manager()
        if pm is None:
            return None
        return {
            "project_dir": str(pm.project_dir),
            "assets_dir": str(pm.assets_dir),
            "project_name": pm.project_name,
        }

    def _handle_project_add_image(kwargs: dict[str, Any]) -> str:
        pm = _get_active_project_manager()
        if pm is None:
            raise RuntimeError("No project is currently open.")
        with _project_write_lock:
            return pm.add_image(
                kwargs["filepath"], kwargs["copy_to_workspace"], kwargs.get("subfolder")
            )

    def _handle_project_get_asset_path(kwargs: dict[str, Any]) -> str | None:
        pm = _get_active_project_manager()
        if pm is None:
            return None
        path = pm.get_asset_path(kwargs["file_hash"])
        return str(path) if path else None

    def _handle_project_save_workflow(kwargs: dict[str, Any]) -> str:
        pm = _get_active_project_manager()
        if pm is None:
            raise RuntimeError("No project is currently open.")
        with _project_write_lock:
            return pm.save_workflow(
                module_id=kwargs["module_id"],
                payload=kwargs["payload"],
                metadata=kwargs["metadata"],
                filename=kwargs.get("filename"),
                attachments=kwargs.get("attachments") or [],
            )

    def _handle_project_load_workflow_payload(kwargs: dict[str, Any]) -> dict[str, Any]:
        pm = _get_active_project_manager()
        if pm is None:
            raise RuntimeError("No project is currently open.")
        return pm.load_workflow_payload(kwargs["filename"])

    def _handle_project_attach_workflow_file(kwargs: dict[str, Any]) -> dict[str, Any]:
        pm = _get_active_project_manager()
        if pm is None:
            raise RuntimeError("No project is currently open.")
        with _project_write_lock:
            return pm.attach_workflow_file(
                wf_filename=kwargs["wf_filename"],
                source_path=kwargs["source_path"],
                key=kwargs["key"],
                description=kwargs.get("description", ""),
                mime_hint=kwargs.get("mime_hint", "application/octet-stream"),
            )

    def _handle_project_list_workflows(_kwargs: dict[str, Any]) -> list[dict[str, Any]]:
        pm = _get_active_project_manager()
        return pm.workflows.list_all() if pm is not None else []

    def _handle_project_load_attachments(kwargs: dict[str, Any]) -> list[dict[str, Any]]:
        pm = _get_active_project_manager()
        if pm is None:
            return []
        return pm.workflows.load_attachments(kwargs["filename"])

    server.register("diagnostics.report_error", _handle_report_error)
    server.register("theme.get_current_colors", _handle_get_current_colors)
    server.register("theme.list_categorized_themes", _handle_list_themes)
    server.register("theme.switch_theme", _handle_switch_theme)
    server.register("menu.get_about_karcytics", _handle_get_about_karcytics)
    server.register("menu.get_about_developer", _handle_get_about_developer)
    server.register("project.get_info", _handle_project_get_info)
    server.register("project.add_image", _handle_project_add_image)
    server.register("project.get_asset_path", _handle_project_get_asset_path)
    server.register("project.save_workflow", _handle_project_save_workflow)
    server.register("project.load_workflow_payload", _handle_project_load_workflow_payload)
    server.register("project.attach_workflow_file", _handle_project_attach_workflow_file)
    server.register("project.list_workflows", _handle_project_list_workflows)
    server.register("project.load_attachments", _handle_project_load_attachments)

    server.start()
    PluginUIDaemon.set_core_services(server.port, server.token)
    logger.info("CoreServicesServer started on port %d", server.port)
    return server
