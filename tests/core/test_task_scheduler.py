"""Tests for TaskScheduler and centralized concurrency management."""

import pytest
from PyQt6.QtCore import QCoreApplication
from biopro.core.task_scheduler import TaskScheduler
from biopro.sdk.core.analysis import AnalysisBase
from biopro.sdk.core.state import PluginState

class MockState(PluginState):
    def __init__(self, value=0):
        self.value = value
    def to_dict(self): return {"value": self.value}
    @classmethod
    def from_dict(cls, d): return cls(d["value"])

class MockAnalyzer(AnalysisBase):
    def run(self, state):
        if state.value == -1:
            raise ValueError("Intentional Error")
        return {"result": state.value * 2}

@pytest.fixture
def scheduler():
    """Returns a fresh-ish TaskScheduler instance."""
    # Since it's a singleton, we clear it between tests if possible
    # or just trust the isolation.
    return TaskScheduler()

class TestTaskScheduler:
    """Test suite for the centralized TaskScheduler."""

    def test_singleton_nature(self):
        """Verifies that TaskScheduler follows the singleton pattern."""
        s1 = TaskScheduler()
        s2 = TaskScheduler()
        assert s1 is s2

    def test_task_submission_and_success(self, qtbot, scheduler):
        """Verifies that a submitted task executes and returns results via signals."""
        analyzer = MockAnalyzer("test_success")
        state = MockState(21)
        
        # We'll collect signals
        results_received = {}
        
        def on_finished(tid, res):
            results_received[tid] = res
            
        scheduler.task_finished.connect(on_finished)
        
        with qtbot.waitSignal(scheduler.task_finished, timeout=1000):
            task_id = scheduler.submit(analyzer, state)
            assert task_id is not None
            
        assert task_id in results_received
        assert results_received[task_id]["result"] == 42
        
        # Verify internal cleanup
        assert task_id not in scheduler._active_workers

    def test_task_error_propagation(self, qtbot, scheduler):
        """Verifies that errors in tasks are caught and propagated globally."""
        analyzer = MockAnalyzer("test_error")
        state = MockState(-1) # Triggers ValueError
        
        errors_received = {}
        
        def on_error(tid, msg):
            errors_received[tid] = msg
            
        scheduler.task_error.connect(on_error)
        
        with qtbot.waitSignal(scheduler.task_error, timeout=1000):
            task_id = scheduler.submit(analyzer, state)
            
        assert task_id in errors_received
        assert "Intentional Error" in errors_received[task_id]
        
        # Verify internal cleanup
        assert task_id not in scheduler._active_workers

    def test_concurrent_execution(self, qtbot, scheduler):
        """Verifies that multiple tasks can be submitted and run concurrently."""
        analyzer1 = MockAnalyzer("task1")
        analyzer2 = MockAnalyzer("task2")
        
        finished_ids = []
        scheduler.task_finished.connect(lambda tid, _: finished_ids.append(tid))
        
        # Submit two tasks
        tid1 = scheduler.submit(analyzer1, MockState(10))
        tid2 = scheduler.submit(analyzer2, MockState(20))
        
        # Wait for both (we expect two finished signals)
        qtbot.waitUntil(lambda: len(finished_ids) == 2, timeout=2000)
        
        assert tid1 in finished_ids
        assert tid2 in finished_ids
