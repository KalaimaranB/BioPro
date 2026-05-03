import logging
from biopro.sdk.utils.logging import get_logger, PluginLoggerAdapter

def test_get_logger_standard():
    logger = get_logger("test_std")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_std"

def test_get_logger_plugin():
    logger = get_logger("test_plugin", plugin_id="my_plugin")
    assert isinstance(logger, PluginLoggerAdapter)
    assert logger.plugin_id == "my_plugin"

def test_plugin_logger_metadata():
    # Capture logs to verify metadata
    class CapturingHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records = []
        def emit(self, record):
            self.records.append(record)
            
    handler = CapturingHandler()
    logger = get_logger("test_meta", plugin_id="meta_plugin")
    logger.logger.addHandler(handler) # Add to the underlying logger
    
    logger.info("Hello with metadata")
    
    assert len(handler.records) == 1
    record = handler.records[0]
    assert record.msg == "Hello with metadata"
    assert getattr(record, "plugin_id") == "meta_plugin"
