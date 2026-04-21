"""Tests for the BioPro Event Bus (The Nervous System)."""

import pytest
import time
from unittest.mock import MagicMock
from PyQt6.QtCore import QThread
from biopro.core.event_bus import EventManager, BioProEvent

class TestEventBus:
    @pytest.fixture
    def bus(self, qtbot):
        """Dedicated EventManager instance for testing."""
        manager = EventManager()
        return manager

    def test_emit_receive(self, bus):
        """Verify basic publish/subscribe functionality."""
        callback = MagicMock()
        bus.subscribe(BioProEvent.PLUGIN_INSTALLED, callback)
        
        bus.emit(BioProEvent.PLUGIN_INSTALLED, "test_plugin")
        
        # We need to process events because dispatch happens via internal signal
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        callback.assert_called_once_with("test_plugin")

    def test_multiple_listeners(self, bus):
        """Verify multiple subscribers can listen to the same event."""
        cb1 = MagicMock()
        cb2 = MagicMock()
        bus.subscribe(BioProEvent.PLUGIN_INSTALLED, cb1)
        bus.subscribe(BioProEvent.PLUGIN_INSTALLED, cb2)
        
        bus.emit(BioProEvent.PLUGIN_INSTALLED, "shared_msg")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        cb1.assert_called_once_with("shared_msg")
        cb2.assert_called_once_with("shared_msg")

    def test_unsubscribe(self, bus):
        """Verify that listeners can be removed."""
        callback = MagicMock()
        bus.subscribe(BioProEvent.PLUGIN_INSTALLED, callback)
        bus.unsubscribe(BioProEvent.PLUGIN_INSTALLED, callback)
        
        bus.emit(BioProEvent.PLUGIN_INSTALLED, "gone")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        callback.assert_not_called()

    def test_cross_thread_emit(self, bus, qtbot):
        """Ensure background threads can safely emit events to UI listeners."""
        received_data = []
        
        def listener(data):
            received_data.append(data)
            
        bus.subscribe(BioProEvent.PLUGIN_INSTALLED, listener)
        
        # Define a worker thread that emits an event
        class Worker(QThread):
            def run(self):
                bus.emit(BioProEvent.PLUGIN_INSTALLED, "from_bg_thread")
        
        worker = Worker()
        worker.start()
        
        # Wait for the worker to finish and process events
        qtbot.waitUntil(lambda: len(received_data) > 0, timeout=2000)
        
        assert received_data[0] == "from_bg_thread"

    def test_error_resilience(self, bus):
        """Verify that one crashing listener doesn't stop the whole bus."""
        def buggy_listener(_):
            raise RuntimeError("Boom!")
            
        cb_healthy = MagicMock()
        
        bus.subscribe(BioProEvent.PLUGIN_INSTALLED, buggy_listener)
        bus.subscribe(BioProEvent.PLUGIN_INSTALLED, cb_healthy)
        
        # Should not crash the emitter
        bus.emit(BioProEvent.PLUGIN_INSTALLED, "data")
        
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        cb_healthy.assert_called_once()
