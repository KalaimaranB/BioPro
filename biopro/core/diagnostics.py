"""BioPro Diagnostic & Error Management Engine.

Provides centralized error handling, black-box logging, and system health monitoring.
"""

import logging
import traceback
from collections import deque
from datetime import datetime
from typing import Any

from biopro.core.event_bus import BioProEvent, event_bus


class BlackBoxHandler(logging.Handler):
    """Memory-resident logging handler that keeps the last N records.

    Acts like an airplane's black box, allowing us to see what happened
    just before a crash.
    """

    def __init__(self, capacity: int = 100):
        super().__init__()
        self.capacity = capacity
        self.records: deque[dict[str, Any]] = deque(maxlen=capacity)

    def emit(self, record):
        try:
            msg = self.format(record)
            self.records.append(
                {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "name": record.name,
                    "message": msg,
                    "plugin_id": getattr(record, "plugin_id", None),
                }
            )
        except Exception:
            self.handleError(record)

    def get_history(self) -> list[dict[str, Any]]:
        """Return the captured history as a list of dicts."""
        return list(self.records)


class DiagnosticEngine:
    """Central nervous system for application health and error reporting."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.black_box = BlackBoxHandler()
        self.black_box.setFormatter(
            logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
        )

        # Attach black box to the root logger so it sees everything
        logging.getLogger().addHandler(self.black_box)

        # Throttling state
        self._last_error_sig = None
        self._last_error_time = 0.0

        self._initialized = True

    def report_error(
        self,
        message: str,
        exception: Exception | None = None,
        plugin_id: str | None = None,
        fatal: bool = False,
    ):
        """Report an error to the system.

        This will log the error and broadcast it via the Event Bus for UI display.
        """
        import time

        now = time.time()
        error_sig = f"{message}|{str(exception)}"

        # Throttle identical errors to max 1 per 2 seconds to prevent dialog storms
        if self._last_error_sig == error_sig and (now - self._last_error_time) < 2.0:
            return

        self._last_error_sig = error_sig
        self._last_error_time = now

        tb = traceback.format_exc() if exception else None

        error_data = {
            "message": message,
            "exception": str(exception) if exception else None,
            "traceback": tb,
            "plugin_id": plugin_id,
            "fatal": fatal,
            "timestamp": datetime.now().isoformat(),
            "history": self.black_box.get_history(),
        }

        # Log it officially
        logger = logging.getLogger("biopro.core.diagnostics")
        log_msg = f"Error Reported: {message}"
        if plugin_id:
            log_msg = f"[{plugin_id}] {log_msg}"

        if fatal:
            logger.critical(log_msg, extra={"plugin_id": plugin_id})
        else:
            logger.error(log_msg, extra={"plugin_id": plugin_id})

        # Broadcast to UI
        event_bus.emit(BioProEvent.ERROR_OCCURRED, error_data)

    def get_full_diagnostic_report(self) -> dict[str, Any]:
        """Generate a complete snapshot of the system state for debugging."""
        return {
            "timestamp": datetime.now().isoformat(),
            "history": self.black_box.get_history(),
            # Future: add hardware stats, loaded plugins, etc.
        }


# Singleton accessor
diagnostics = DiagnosticEngine()
