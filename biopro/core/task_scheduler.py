"""Centralized Task Scheduler for BioPro.

Manages a global thread pool to execute long-running analysis tasks,
preventing thread exhaustion and ensuring UI responsiveness.
"""

import logging
import uuid
from functools import partial
from typing import Optional

from biopro_sdk.core.analysis import AnalysisBase, AnalysisRunnable, AnalysisWorker
from biopro_sdk.core.state import PluginState
from PyQt6.QtCore import QObject, QThreadPool, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)


class TaskScheduler(QObject):
    """Singleton manager for background computations.

    Provides a central point for task submission, monitoring, and
    resource management. Integration with BioPro's Nervous System
    via task lifecycle signals.
    """

    # Lifecycle signals for global monitoring and debugging
    task_started = pyqtSignal(str)  # task_id
    task_finished = pyqtSignal(str, dict)  # task_id, results
    task_error = pyqtSignal(str, str)  # task_id, error_message
    task_progress = pyqtSignal(str, int)  # task_id, progress (0-100)

    _instance: Optional["TaskScheduler"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        super().__init__()
        self.pool = QThreadPool.globalInstance()

        # Retain references to active workers to prevent Python's GC
        # from reclaiming them while the C++ thread is still running.
        self._active_workers: dict[str, AnalysisWorker] = {}

        self._initialized = True
        logger.info(f"TaskScheduler initialized. Thread pool limit: {self.pool.maxThreadCount()}")

    def submit(self, analyzer: AnalysisBase, state: PluginState | None = None) -> AnalysisWorker:
        """Submit an analysis task to the central thread pool.

        Args:
            analyzer: Instance of AnalysisBase subclass containing the logic.
            state: Instance of PluginState containing parameters (optional).

        Returns:
            The AnalysisWorker instance for signal connection.
        """
        try:
            task_id = str(uuid.uuid4())

            # 1. Create the worker (The QObject that does the work and talks to the UI)
            worker = AnalysisWorker(analyzer, state, parent=self)
            worker.task_id = task_id  # Attach ID for tracking

            # 2. Bridge worker signals to the global scheduler signals
            worker.finished.connect(partial(self._on_task_finished, task_id))
            worker.error.connect(partial(self._on_task_error, task_id))
            worker.progress.connect(partial(self.task_progress.emit, task_id))

            # Connect to deleteLater to schedule safe automatic cleanup
            worker.finished.connect(worker.deleteLater)
            worker.error.connect(worker.deleteLater)
            worker.cancelled.connect(worker.deleteLater)

            # 3. Track active workers (releases on completion via _cleanup)
            self._active_workers[task_id] = worker

            # 4. Wrap and schedule
            runnable = AnalysisRunnable(worker)
            self.task_started.emit(task_id)
            self.pool.start(runnable)

            logger.debug(f"Submitted task {task_id} ({analyzer.plugin_id}) to pool.")
            return worker
        except Exception as e:
            logger.error(f"Failed to submit task to scheduler: {e}")
            try:
                from biopro.core.diagnostics import diagnostics

                diagnostics.report_error(f"Failed to submit task to scheduler: {e}", exception=e)
            except Exception:
                pass
            raise e

    def cancel_all(self) -> None:
        """Attempt to stop all pending tasks in the pool."""
        self.pool.clear()
        logger.warning("Task pool cleared. Pending tasks cancelled.")

    def shutdown(self) -> None:
        """Gracefully shutdown the scheduler, waiting for active tasks."""
        logger.info("TaskScheduler shutting down...")
        self.pool.clear()
        # Wait up to 2 seconds for active threads to finish or abort safely
        self.pool.waitForDone(2000)
        self._active_workers.clear()

    @pyqtSlot(str, dict)
    def _on_task_finished(self, task_id: str, results: dict):
        self.task_finished.emit(task_id, results)
        self._cleanup(task_id)

    @pyqtSlot(str, str)
    def _on_task_error(self, task_id: str, error_msg: str):
        self.task_error.emit(task_id, error_msg)
        logger.error(f"Background task {task_id} failed: {error_msg}")
        try:
            from biopro.core.diagnostics import diagnostics

            diagnostics.report_error(f"Background task failed: {error_msg}")
        except Exception:
            pass
        self._cleanup(task_id)

    def _cleanup(self, task_id: str):
        """Release worker reference so it can be garbage collected."""
        if task_id in self._active_workers:
            worker = self._active_workers[task_id]
            try:
                worker.finished.disconnect()
                worker.error.disconnect()
                worker.progress.disconnect()
                worker.setParent(None)
            except (RuntimeError, TypeError):
                pass  # Already deleted or signals not connected
            del self._active_workers[task_id]


# Singleton instance for application-wide use
task_scheduler = TaskScheduler()
