"""Centralized Task Scheduler for BioPro.

Manages a global thread pool to execute long-running analysis tasks,
preventing thread exhaustion and ensuring UI responsiveness.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from PyQt6.QtCore import QObject, QThreadPool, pyqtSignal, pyqtSlot

from biopro.sdk.core.analysis import AnalysisBase, AnalysisWorker, AnalysisRunnable
from biopro.sdk.core.state import PluginState
from biopro.sdk.core.managed_task import FunctionalTask

logger = logging.getLogger(__name__)


class TaskScheduler(QObject):
    """Singleton manager for background computations.
    
    Provides a central point for task submission, monitoring, and 
    resource management. Integration with BioPro's Nervous System
    via task lifecycle signals.
    """
    
    # Lifecycle signals for global monitoring and debugging
    task_started = pyqtSignal(str)          # task_id
    task_finished = pyqtSignal(str, dict)    # task_id, results
    task_error = pyqtSignal(str, str)       # task_id, error_message
    task_progress = pyqtSignal(str, int)    # task_id, progress (0-100)
    
    _instance: Optional['TaskScheduler'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskScheduler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
            
        super().__init__()
        self.pool = QThreadPool.globalInstance()
        
        # Retain references to active workers to prevent Python's GC 
        # from reclaiming them while the C++ thread is still running.
        self._active_workers: Dict[str, AnalysisWorker] = {}
        
        self._initialized = True
        logger.info(
            f"TaskScheduler initialized. Thread pool limit: {self.pool.maxThreadCount()}"
        )

    def submit(self, analyzer: AnalysisBase, state: PluginState) -> str:
        """Submit an analysis task to the central thread pool.
        
        Args:
            analyzer: Instance of AnalysisBase subclass containing the logic.
            state: Instance of PluginState containing parameters.
            
        Returns:
            A unique task_id (UUID string) for tracking.
        """
        task_id = str(uuid.uuid4())
        
        # 1. Create the worker (The QObject that does the work and talks to the UI)
        worker = AnalysisWorker(analyzer, state)
        
        # 2. Bridge worker signals to the global scheduler signals
        # Use keyword arguments or local functions to capture task_id correctly
        worker.finished.connect(lambda results: self._on_task_finished(task_id, results))
        worker.error.connect(lambda error_msg: self._on_task_error(task_id, error_msg))
        worker.progress.connect(lambda p: self.task_progress.emit(task_id, p))
        
        # 3. Prevent GC
        self._active_workers[task_id] = worker
        
        # 4. Wrap and schedule
        runnable = AnalysisRunnable(worker)
        self.task_started.emit(task_id)
        self.pool.start(runnable)
        
        logger.debug(f"Submitted task {task_id} ({analyzer.plugin_id}) to pool.")
        return task_id

    def cancel_all(self) -> None:
        """Attempt to stop all pending tasks in the pool."""
        self.pool.clear()
        logger.warning("Task pool cleared. Pending tasks cancelled.")

    @pyqtSlot(str, dict)
    def _on_task_finished(self, task_id: str, results: dict):
        self.task_finished.emit(task_id, results)
        self._cleanup(task_id)

    @pyqtSlot(str, str)
    def _on_task_error(self, task_id: str, error_msg: str):
        self.task_error.emit(task_id, error_msg)
        self._cleanup(task_id)

    def _cleanup(self, task_id: str):
        """Release worker reference so it can be garbage collected."""
        if task_id in self._active_workers:
            del self._active_workers[task_id]


# Singleton instance for application-wide use
task_scheduler = TaskScheduler()
