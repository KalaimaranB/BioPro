"""Start the CoreServicesServer and register loopback bridge services for isolated modules.

Task scheduling is deliberately *not* exposed here. An isolated module runs
its own local task scheduler inside its own process (see the SDK's
`ui_daemon_runtime` and its `PluginContext`-injected services) — routing
every analysis run through IPC to the Hub would add latency for no
isolation benefit, per the same reasoning already applied when Flow
Cytometry's `ui_daemon.py` was first prototyped. Only state that genuinely
lives in the Hub (diagnostics reporting today; project I/O and theme
queries as isolated modules need them) belongs behind this loopback bridge.
"""

from __future__ import annotations

import logging
from typing import Any

from karcytics_sdk.host.core_services import CoreServicesServer
from karcytics_sdk.plugin.daemon import PluginUIDaemon

logger = logging.getLogger(__name__)


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


def start_core_services() -> CoreServicesServer:
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

    server.register("diagnostics.report_error", _handle_report_error)
    server.register("theme.get_current_colors", _handle_get_current_colors)
    server.register("theme.list_categorized_themes", _handle_list_themes)
    server.register("theme.switch_theme", _handle_switch_theme)

    server.start()
    PluginUIDaemon.set_core_services(server.port, server.token)
    logger.info("CoreServicesServer started on port %d", server.port)
    return server
