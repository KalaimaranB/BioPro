import logging
import pytest
from biopro.core.diagnostics import DiagnosticEngine, BlackBoxHandler
from biopro.core.event_bus import event_bus, BioProEvent

def test_black_box_capacity():
    handler = BlackBoxHandler(capacity=5)
    logger = logging.getLogger("test_bb")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    for i in range(10):
        logger.info(f"Message {i}")
        
    history = handler.get_history()
    assert len(history) == 5
    assert history[-1]["message"] == "Message 9"
    assert history[0]["message"] == "Message 5"

def test_diagnostic_engine_singleton():
    d1 = DiagnosticEngine()
    d2 = DiagnosticEngine()
    assert d1 is d2

def test_error_reporting(qtbot):
    engine = DiagnosticEngine()
    
    received_data = []
    def on_error(data):
        received_data.append(data)
        
    event_bus.subscribe(BioProEvent.ERROR_OCCURRED, on_error)
    
    try:
        raise ValueError("Test Error")
    except ValueError as e:
        engine.report_error("Test failure message", exception=e, plugin_id="test_plugin")
        
    assert len(received_data) == 1
    data = received_data[0]
    assert data["message"] == "Test failure message"
    assert "Test Error" in data["exception"]
    assert data["plugin_id"] == "test_plugin"
    assert "traceback" in data
    assert len(data["history"]) > 0

def test_black_box_formatting():
    handler = BlackBoxHandler(capacity=1)
    handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    
    record = logging.LogRecord("test", logging.INFO, "path", 10, "Formatted message", None, None)
    handler.emit(record)
    
    history = handler.get_history()
    assert history[0]["message"] == "INFO - Formatted message"
