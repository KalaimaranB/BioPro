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


def start_core_services() -> CoreServicesServer:
    """Start the Hub's `CoreServicesServer` and register its handlers.

    Records the server port on `PluginUIDaemon` so every isolated module spawned
    from here on can reach it.

    Call once, early in Hub startup. The caller owns the returned server's
    lifetime and must call `.stop()` on shutdown (e.g. via `QApplication
    .aboutToQuit`).
    """
    from karcytics.core.diagnostics import diagnostics

    server = CoreServicesServer()

    def _handle_report_error(kwargs: dict[str, Any]) -> dict[str, str]:
        diagnostics.report_error(
            message=kwargs.get("message", ""),
            plugin_id=kwargs.get("plugin_id"),
            fatal=kwargs.get("fatal", False),
        )
        return {"status": "ok"}

    server.register("diagnostics.report_error", _handle_report_error)

    server.start()
    PluginUIDaemon.set_core_services_port(server.port)
    logger.info("CoreServicesServer started on port %d", server.port)
    return server
